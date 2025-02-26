#!/usr/bin/env python3
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import itertools
import json
import logging
from pathlib import Path
import concurrent.futures
from dataclasses import dataclass
import random
from deap import base, creator, tools, algorithms

from ..core.strategy.gann_strategy import GannStrategy
from ..core.data.historical_data import HistoricalDataManager
from .backtest import BacktestEngine
from ..core.utils.logger import setup_logger

logger = setup_logger('optimize')

@dataclass
class OptimizationResult:
    """Container for optimization results"""
    parameters: Dict
    metrics: Dict
    backtest_results: Dict
    optimization_time: float

class StrategyOptimizer:
    def __init__(self, config: Dict):
        """Initialize strategy optimizer"""
        self.config = config
        self.data_manager = HistoricalDataManager(config)
        self.output_dir = Path('optimization_results')
        self.output_dir.mkdir(exist_ok=True)
        
        # Parameter ranges for optimization
        self.param_ranges = {
            'gann_increments': [
                [0.125, 0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25],
                [0.25, 0.5, 0.75, 1.0, 1.25, 1.0, 0.75, 0.5],
                [0.5, 0.75, 1.0, 1.25, 1.5, 1.25, 1.0, 0.75]
            ],
            'num_values': list(range(20, 51, 5)),  # 20 to 50 step 5
            'buffer_percentage': [0.001, 0.002, 0.003, 0.004, 0.005],
            'num_targets': [2, 3, 4, 5],
            'trailing_stop': [0.002, 0.003, 0.004, 0.005]
        }
        
    async def grid_search(self,
                         symbol: str,
                         start_date: datetime,
                         end_date: datetime,
                         metric: str = 'sharpe_ratio',
                         max_workers: int = 4) -> List[OptimizationResult]:
        """Perform grid search optimization"""
        try:
            logger.info("Starting grid search optimization...")
            start_time = datetime.now()
            
            # Generate parameter combinations
            param_combinations = self._generate_param_combinations()
            logger.info(f"Generated {len(param_combinations)} parameter combinations")
            
            # Run backtests in parallel
            results = []
            with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for params in param_combinations:
                    future = executor.submit(
                        self._run_backtest_with_params,
                        symbol,
                        start_date,
                        end_date,
                        params
                    )
                    futures.append(future)
                
                # Collect results
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                        logger.debug(f"Completed backtest: {result.metrics[metric]}")
                    except Exception as e:
                        logger.error(f"Error in backtest: {e}")
            
            # Sort results by metric
            results.sort(key=lambda x: x.metrics[metric], reverse=True)
            
            # Save results
            self._save_optimization_results(results, 'grid_search', start_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in grid search: {e}")
            raise

    async def genetic_optimize(self,
                             symbol: str,
                             start_date: datetime,
                             end_date: datetime,
                             population_size: int = 50,
                             generations: int = 30,
                             metric: str = 'sharpe_ratio') -> List[OptimizationResult]:
        """Perform genetic algorithm optimization"""
        try:
            logger.info("Starting genetic optimization...")
            start_time = datetime.now()
            
            # Setup genetic algorithm
            creator.create("FitnessMax", base.Fitness, weights=(1.0,))
            creator.create("Individual", list, fitness=creator.FitnessMax)
            
            toolbox = base.Toolbox()
            
            # Register genetic operators
            toolbox.register("attr_float", random.uniform, 0, 1)
            toolbox.register("individual", tools.initRepeat, creator.Individual,
                           toolbox.attr_float, n=len(self.param_ranges))
            toolbox.register("population", tools.initRepeat, list, toolbox.individual)
            
            # Define evaluation function
            def evaluate(individual):
                params = self._decode_individual(individual)
                result = self._run_backtest_with_params(
                    symbol, start_date, end_date, params
                )
                return (result.metrics[metric],)
            
            toolbox.register("evaluate", evaluate)
            toolbox.register("mate", tools.cxTwoPoint)
            toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=1, indpb=0.2)
            toolbox.register("select", tools.selTournament, tournsize=3)
            
            # Create initial population
            pop = toolbox.population(n=population_size)
            
            # Run evolution
            stats = tools.Statistics(key=lambda ind: ind.fitness.values)
            stats.register("avg", np.mean)
            stats.register("std", np.std)
            stats.register("min", np.min)
            stats.register("max", np.max)
            
            final_pop, logbook = algorithms.eaSimple(
                pop, toolbox,
                cxpb=0.7,  # crossover probability
                mutpb=0.2,  # mutation probability
                ngen=generations,
                stats=stats,
                verbose=True
            )
            
            # Get best individuals
            best_individuals = tools.selBest(final_pop, k=10)
            results = []
            
            for ind in best_individuals:
                params = self._decode_individual(ind)
                result = self._run_backtest_with_params(
                    symbol, start_date, end_date, params
                )
                results.append(result)
            
            # Save results
            self._save_optimization_results(results, 'genetic', start_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in genetic optimization: {e}")
            raise

    def _generate_param_combinations(self) -> List[Dict]:
        """Generate all parameter combinations"""
        param_names = list(self.param_ranges.keys())
        param_values = list(self.param_ranges.values())
        
        combinations = []
        for values in itertools.product(*param_values):
            params = dict(zip(param_names, values))
            combinations.append(params)
            
        return combinations

    def _decode_individual(self, individual: List[float]) -> Dict:
        """Decode genetic algorithm individual to parameters"""
        params = {}
        for i, (param_name, param_range) in enumerate(self.param_ranges.items()):
            if isinstance(param_range[0], list):
                # For list parameters (like gann_increments)
                index = int(individual[i] * len(param_range))
                params[param_name] = param_range[min(index, len(param_range)-1)]
            else:
                # For numeric parameters
                min_val = min(param_range)
                max_val = max(param_range)
                params[param_name] = min_val + individual[i] * (max_val - min_val)
                
                # Round to appropriate precision
                if isinstance(min_val, int):
                    params[param_name] = int(round(params[param_name]))
                else:
                    params[param_name] = round(params[param_name], 6)
        
        return params

    def _run_backtest_with_params(self,
                                 symbol: str,
                                 start_date: datetime,
                                 end_date: datetime,
                                 params: Dict) -> OptimizationResult:
        """Run backtest with specific parameters"""
        try:
            # Update config with new parameters
            config = self.config.copy()
            config.update(params)
            
            # Run backtest
            backtest = BacktestEngine(config)
            results = backtest.run_backtest(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            return OptimizationResult(
                parameters=params,
                metrics=results['metrics'],
                backtest_results=results,
                optimization_time=datetime.now().timestamp()
            )
            
        except Exception as e:
            logger.error(f"Error in backtest run: {e}")
            raise

    def _save_optimization_results(self,
                                 results: List[OptimizationResult],
                                 method: str,
                                 start_time: datetime):
        """Save optimization results"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = self.output_dir / f"{method}_optimization_{timestamp}.json"
            
            output = {
                'method': method,
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'results': [
                    {
                        'parameters': r.parameters,
                        'metrics': r.metrics,
                        'optimization_time': r.optimization_time
                    }
                    for r in results
                ]
            }
            
            with open(filename, 'w') as f:
                json.dump(output, f, indent=4)
                
            logger.info(f"Saved optimization results to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving optimization results: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Optimize strategy parameters')
    
    parser.add_argument('--symbol', type=str, required=True, help='Trading symbol')
    parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--method', type=str, choices=['grid', 'genetic'], default='grid',
                        help='Optimization method')
    parser.add_argument('--metric', type=str, default='sharpe_ratio',
                        help='Optimization metric')
    parser.add_argument('--config', type=str, default='config/trading_config.json',
                        help='Config file')
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = json.load(f)
    
    # Run optimization
    optimizer = StrategyOptimizer(config)
    
    if args.method == 'grid':
        results = optimizer.grid_search(
            symbol=args.symbol,
            start_date=datetime.strptime(args.start, '%Y-%m-%d'),
            end_date=datetime.strptime(args.end, '%Y-%m-%d'),
            metric=args.metric
        )
    else:
        results = optimizer.genetic_optimize(
            symbol=args.symbol,
            start_date=datetime.strptime(args.start, '%Y-%m-%d'),
            end_date=datetime.strptime(args.end, '%Y-%m-%d'),
            metric=args.metric
        )
    
    print("\nTop 5 Parameter Sets:")
    for i, result in enumerate(results[:5], 1):
        print(f"\n{i}. Parameters:")
        for param, value in result.parameters.items():
            print(f"   {param}: {value}")
        print(f"   {args.metric}: {result.metrics[args.metric]:.4f}")