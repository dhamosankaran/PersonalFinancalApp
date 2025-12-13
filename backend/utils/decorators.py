"""
Utility decorators for metrics collection and observability.
"""

import functools
import time
import asyncio
from typing import Callable, Optional, Any
from services.metrics import metrics_collector, Timer


def timed_operation(
    flow: str, 
    operation: Optional[str] = None,
    include_args: bool = False
):
    """
    Decorator to time a function and record metrics.
    
    Args:
        flow: The flow name (e.g., 'rag', 'embedding')
        operation: The operation name (defaults to function name)
        include_args: Whether to include function args in metadata
    
    Usage:
        @timed_operation(flow="rag", operation="query")
        async def query(self, question: str):
            ...
    """
    def decorator(func: Callable):
        op_name = operation or func.__name__
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            metadata = {}
            if include_args:
                # Include safe-to-log kwargs
                safe_kwargs = {k: str(v)[:100] for k, v in kwargs.items() 
                               if not k.startswith('_')}
                metadata["kwargs"] = safe_kwargs
            
            with Timer(flow, op_name, metadata=metadata):
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            metadata = {}
            if include_args:
                safe_kwargs = {k: str(v)[:100] for k, v in kwargs.items() 
                               if not k.startswith('_')}
                metadata["kwargs"] = safe_kwargs
            
            with Timer(flow, op_name, metadata=metadata):
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def track_errors(flow: str, error_type: str = "general"):
    """
    Decorator to track errors for a flow.
    
    Args:
        flow: The flow name
        error_type: Type of error for categorization
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                metrics_collector.record_error(flow, error_type)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                metrics_collector.record_error(flow, error_type)
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def count_operation(flow: str, counter_name: str, value: int = 1):
    """
    Decorator to count operations.
    
    Args:
        flow: The flow name
        counter_name: Name of the counter to increment
        value: Value to increment by
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            metrics_collector.increment_counter(flow, counter_name, value)
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            metrics_collector.increment_counter(flow, counter_name, value)
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
