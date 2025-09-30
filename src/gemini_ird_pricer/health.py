"""Enhanced health check endpoints with dependency validation."""

from __future__ import annotations
import os
import time
from typing import Dict, Any, List
from flask import Flask, jsonify, current_app
import pandas as pd
import numpy as np


class HealthChecker:
    """Comprehensive health check implementation."""
    
    def __init__(self, app: Flask = None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize health checker with Flask app."""
        app.add_url_rule('/health', 'health', self.health_check)
        app.add_url_rule('/ready', 'ready', self.readiness_check)
        app.add_url_rule('/live', 'live', self.liveness_check)
    
    def liveness_check(self) -> tuple[Dict[str, Any], int]:
        """Basic liveness probe - always returns OK if service is running."""
        return jsonify({
            'status': 'ok',
            'timestamp': time.time(),
            'service': 'gemini-ird-pricer'
        }), 200
    
    def readiness_check(self) -> tuple[Dict[str, Any], int]:
        """Readiness probe - checks if service can handle requests."""
        checks = []
        overall_status = 'ok'
        
        # Check data directory
        data_dir_status = self._check_data_directory()
        checks.append(data_dir_status)
        if data_dir_status['status'] != 'ok':
            overall_status = 'degraded'
        
        # Check dependencies
        deps_status = self._check_dependencies()
        checks.append(deps_status)
        if deps_status['status'] != 'ok':
            overall_status = 'error'
        
        # Check curve files
        curve_status = self._check_curve_files()
        checks.append(curve_status)
        if curve_status['status'] != 'ok':
            overall_status = 'degraded'
        
        status_code = 200 if overall_status == 'ok' else 503
        
        return jsonify({
            'status': overall_status,
            'timestamp': time.time(),
            'checks': checks
        }), status_code
    
    def health_check(self) -> tuple[Dict[str, Any], int]:
        """Comprehensive health check with detailed diagnostics."""
        return self.readiness_check()
    
    def _check_data_directory(self) -> Dict[str, Any]:
        """Check if data directory exists and is accessible."""
        try:
            data_dir = current_app.config.get('DATA_DIR', 'data/curves')
            if os.path.exists(data_dir) and os.access(data_dir, os.R_OK):
                return {
                    'name': 'data_directory',
                    'status': 'ok',
                    'message': f'Data directory accessible: {data_dir}'
                }
            else:
                return {
                    'name': 'data_directory',
                    'status': 'error',
                    'message': f'Data directory not accessible: {data_dir}'
                }
        except Exception as e:
            return {
                'name': 'data_directory',
                'status': 'error',
                'message': f'Data directory check failed: {str(e)}'
            }
    
    def _check_dependencies(self) -> Dict[str, Any]:
        """Check critical dependencies are available."""
        try:
            # Test pandas
            pd.DataFrame({'test': [1, 2, 3]})
            
            # Test numpy
            np.array([1, 2, 3])
            
            return {
                'name': 'dependencies',
                'status': 'ok',
                'message': 'All dependencies available'
            }
        except Exception as e:
            return {
                'name': 'dependencies',
                'status': 'error',
                'message': f'Dependency check failed: {str(e)}'
            }
    
    def _check_curve_files(self) -> Dict[str, Any]:
        """Check if curve files are available."""
        try:
            from .utils import find_curve_file
            
            config = current_app.config
            curve_file = find_curve_file(config)
            
            if curve_file and os.path.exists(curve_file):
                return {
                    'name': 'curve_files',
                    'status': 'ok',
                    'message': f'Curve file available: {os.path.basename(curve_file)}'
                }
            else:
                return {
                    'name': 'curve_files',
                    'status': 'error',
                    'message': 'No curve files found'
                }
        except Exception as e:
            return {
                'name': 'curve_files',
                'status': 'error',
                'message': f'Curve file check failed: {str(e)}'
            }
