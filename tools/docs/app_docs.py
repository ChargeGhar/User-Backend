#!/usr/bin/env python3
"""
Django App Documentation Generator

This script generates comprehensive documentation for Django apps by analyzing
Python source files using AST parsing. It creates AI-friendly markdown
documentation that helps AI agents understand app structure and capabilities.

Usage:
    python app_docs.py --dir <app_name>
    python app_docs.py --dir users
    python app_docs.py --all  # Generate docs for all apps

Author: ChargeGhar Development Team
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class PythonCodeAnalyzer:
    """Analyzes Python code using AST to extract classes, methods, and functions."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.tree = None
        self.analysis_result = {
            'classes': [],
            'functions': [],
            'imports': [],
            'constants': [],
            'file_docstring': None
        }
    
    def parse_file(self) -> bool:
        """Parse the Python file and build AST."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            self.tree = ast.parse(source_code)
            return True
        except Exception as e:
            print(f"Error parsing {self.file_path}: {str(e)}")
            return False
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze the AST and extract relevant information."""
        if not self.parse_file():
            return self.analysis_result
        
        # Get module docstring
        self.analysis_result['file_docstring'] = ast.get_docstring(self.tree)
        
        # Walk through all nodes
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                self._analyze_class(node)
            elif isinstance(node, ast.FunctionDef):
                self._analyze_function(node)
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                self._analyze_import(node)
            elif isinstance(node, ast.Assign):
                self._analyze_assignment(node)
        
        return self.analysis_result
    
    def _analyze_class(self, node: ast.ClassDef) -> None:
        """Analyze a class definition."""
        class_info = {
            'name': node.name,
            'docstring': ast.get_docstring(node),
            'base_classes': [self._get_name(base) for base in node.bases],
            'methods': [],
            'class_variables': [],
            'decorators': [self._get_decorator_name(dec) for dec in node.decorator_list],
            'line_number': node.lineno
        }
        
        # Analyze class methods and properties
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._analyze_method(item)
                class_info['methods'].append(method_info)
            elif isinstance(item, ast.Assign):
                var_info = self._analyze_class_variable(item)
                if var_info:
                    class_info['class_variables'].append(var_info)
        
        self.analysis_result['classes'].append(class_info)
    
    def _analyze_method(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze a method definition."""
        return {
            'name': node.name,
            'docstring': ast.get_docstring(node),
            'args': self._get_function_args(node.args),
            'decorators': [self._get_decorator_name(dec) for dec in node.decorator_list],
            'returns': self._get_return_annotation(node),
            'line_number': node.lineno,
            'is_property': any(self._get_decorator_name(dec) == 'property' for dec in node.decorator_list),
            'is_static': any(self._get_decorator_name(dec) == 'staticmethod' for dec in node.decorator_list),
            'is_class_method': any(self._get_decorator_name(dec) == 'classmethod' for dec in node.decorator_list)
        }
    
    def _analyze_function(self, node: ast.FunctionDef) -> None:
        """Analyze a standalone function definition."""
        func_info = {
            'name': node.name,
            'docstring': ast.get_docstring(node),
            'args': self._get_function_args(node.args),
            'decorators': [self._get_decorator_name(dec) for dec in node.decorator_list],
            'returns': self._get_return_annotation(node),
            'line_number': node.lineno
        }
        
        self.analysis_result['functions'].append(func_info)
    
    def _analyze_import(self, node: Union[ast.Import, ast.ImportFrom]) -> None:
        """Analyze import statements."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                self.analysis_result['imports'].append({
                    'module': alias.name,
                    'alias': alias.asname,
                    'type': 'import'
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                self.analysis_result['imports'].append({
                    'module': module,
                    'name': alias.name,
                    'alias': alias.asname,
                    'type': 'from'
                })
    
    def _analyze_assignment(self, node: ast.Assign) -> None:
        """Analyze module-level assignments (constants)."""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                self.analysis_result['constants'].append({
                    'name': target.id,
                    'value': self._get_value_string(node.value),
                    'line_number': node.lineno
                })
    
    def _analyze_class_variable(self, node: ast.Assign) -> Optional[Dict[str, Any]]:
        """Analyze class variable assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                return {
                    'name': target.id,
                    'value': self._get_value_string(node.value),
                    'line_number': node.lineno
                }
        return None
    
    def _get_function_args(self, args: ast.arguments) -> List[Dict[str, Any]]:
        """Extract function arguments information."""
        result = []
        
        # Regular arguments
        for i, arg in enumerate(args.args):
            arg_info = {
                'name': arg.arg,
                'annotation': self._get_annotation(arg.annotation),
                'default': None
            }
            
            # Check for default values
            defaults_offset = len(args.args) - len(args.defaults)
            if i >= defaults_offset:
                default_index = i - defaults_offset
                arg_info['default'] = self._get_value_string(args.defaults[default_index])
            
            result.append(arg_info)
        
        # Keyword-only arguments
        for i, arg in enumerate(args.kwonlyargs):
            arg_info = {
                'name': arg.arg,
                'annotation': self._get_annotation(arg.annotation),
                'default': None,
                'keyword_only': True
            }
            
            if i < len(args.kw_defaults) and args.kw_defaults[i] is not None:
                arg_info['default'] = self._get_value_string(args.kw_defaults[i])
            
            result.append(arg_info)
        
        # *args
        if args.vararg:
            result.append({
                'name': f"*{args.vararg.arg}",
                'annotation': self._get_annotation(args.vararg.annotation),
                'vararg': True
            })
        
        # **kwargs
        if args.kwarg:
            result.append({
                'name': f"**{args.kwarg.arg}",
                'annotation': self._get_annotation(args.kwarg.annotation),
                'kwarg': True
            })
        
        return result
    
    def _get_annotation(self, annotation: Optional[ast.AST]) -> Optional[str]:
        """Get type annotation as string."""
        if annotation is None:
            return None
        return ast.unparse(annotation) if hasattr(ast, 'unparse') else str(annotation)
    
    def _get_return_annotation(self, node: ast.FunctionDef) -> Optional[str]:
        """Get return type annotation."""
        return self._get_annotation(node.returns)
    
    def _get_decorator_name(self, decorator: ast.AST) -> str:
        """Get decorator name as string."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return ast.unparse(decorator) if hasattr(ast, 'unparse') else str(decorator)
        elif isinstance(decorator, ast.Call):
            return self._get_name(decorator.func)
        return str(decorator)
    
    def _get_name(self, node: ast.AST) -> str:
        """Get name from various AST node types."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
        return str(node)
    
    def _get_value_string(self, node: ast.AST) -> str:
        """Get string representation of a value."""
        try:
            if hasattr(ast, 'unparse'):
                return ast.unparse(node)
            else:
                # Fallback for older Python versions
                if isinstance(node, ast.Constant):
                    return repr(node.value)
                elif isinstance(node, (ast.Str, ast.Num)):
                    return repr(node.n if hasattr(node, 'n') else node.s)
                return str(node)
        except:
            return str(node)


class DjangoAppDocumentationGenerator:
    """Generates comprehensive documentation for Django apps."""
    
    def __init__(self, api_dir: str = "api"):
        self.api_dir = Path(api_dir)
        self.target_files = [
            'models.py',
            'serializers.py', 
            'services.py',
            'tasks.py',
            'permissions.py'
        ]
    
    def get_available_apps(self) -> List[str]:
        """Get list of available Django apps in api directory."""
        if not self.api_dir.exists():
            print(f"API directory {self.api_dir} does not exist!")
            return []
        
        apps = []
        for item in self.api_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                # Check if it has at least one of our target files
                has_target_files = any(
                    (item / filename).exists() for filename in self.target_files
                )
                if has_target_files:
                    apps.append(item.name)
        
        return sorted(apps)
    
    def analyze_app(self, app_name: str) -> Dict[str, Any]:
        """Analyze a single Django app and extract documentation."""
        app_path = self.api_dir / app_name
        
        if not app_path.exists():
            raise ValueError(f"App '{app_name}' does not exist in {self.api_dir}")
        
        app_doc = {
            'app_name': app_name,
            'app_path': str(app_path),
            'analyzed_files': {},
            'summary': {
                'total_classes': 0,
                'total_methods': 0,
                'total_functions': 0,
                'available_files': []
            },
            'generated_at': datetime.now().isoformat()
        }
        
        # Analyze each target file
        for filename in self.target_files:
            file_path = app_path / filename
            
            if file_path.exists():
                print(f"  Analyzing {filename}...")
                analyzer = PythonCodeAnalyzer(str(file_path))
                analysis = analyzer.analyze()
                
                app_doc['analyzed_files'][filename] = analysis
                app_doc['summary']['available_files'].append(filename)
                
                # Update summary counts
                app_doc['summary']['total_classes'] += len(analysis['classes'])
                app_doc['summary']['total_functions'] += len(analysis['functions'])
                
                for cls in analysis['classes']:
                    app_doc['summary']['total_methods'] += len(cls['methods'])
        
        return app_doc
    
    def generate_markdown_documentation(self, app_doc: Dict[str, Any]) -> str:
        """Generate AI-perfect documentation with Features TOC endpoint suggestions."""
        md_content = []
        
        # Simplified header
        md_content.append(f"# {app_doc['app_name'].title()} App - AI Context")
        md_content.append("")
        
        # Quick overview for AI
        summary = app_doc['summary']
        md_content.append("## 🎯 Quick Overview")
        md_content.append("")
        md_content.append(f"**Purpose**: {self._infer_app_purpose(app_doc['app_name'])}")
        md_content.append(f"**Available Components**: {', '.join(summary['available_files'])}")
        md_content.append("")
        
        # Generate endpoint suggestions based on Features TOC
        md_content.extend(self._generate_features_toc_endpoints(app_doc))
        
        # AI-focused analysis for each file
        for filename in sorted(app_doc['analyzed_files'].keys()):
            analysis = app_doc['analyzed_files'][filename]
            md_content.extend(self._generate_ai_optimized_file_docs(filename, analysis))
        
        return "\n".join(md_content)
    
    def _generate_features_toc_endpoints(self, app_doc: Dict[str, Any]) -> List[str]:
        """Generate endpoint suggestions based on Features TOC mapping."""
        content = []
        app_name = app_doc['app_name']
        
        # Define app-to-endpoints mapping based on Features TOC
        endpoint_mappings = {
            'users': [
                {'method': 'POST', 'url': '/api/auth/login', 'purpose': 'Completes login after OTP verification', 'input': 'UserLoginSerializer', 'service': 'AuthService().login_user(validated_data, request)', 'output': '{"user_id": str, "access_token": str, "refresh_token": str}', 'auth': 'No'},
                {'method': 'POST', 'url': '/api/auth/logout', 'purpose': 'Invalidates JWT and clears session', 'input': 'None', 'service': 'AuthService().logout_user(refresh_token, request)', 'output': '{"message": "Logged out"}', 'auth': 'JWT Required'},
                {'method': 'POST', 'url': '/api/auth/register', 'purpose': 'Creates new user account after OTP verification', 'input': 'UserRegistrationSerializer', 'service': 'AuthService().register_user(validated_data, request)', 'output': '{"user_id": str, "access_token": str, "refresh_token": str}', 'auth': 'No'},
                {'method': 'POST', 'url': '/api/auth/otp/request', 'purpose': 'Sends OTP via SMS or Email', 'input': 'OTPRequestSerializer', 'service': 'AuthService().generate_otp(identifier, purpose)', 'output': '{"message": str, "expires_in": int}', 'auth': 'No'},
                {'method': 'POST', 'url': '/api/auth/otp/verify', 'purpose': 'Validates OTP and returns verification token', 'input': 'OTPVerificationSerializer', 'service': 'AuthService().verify_otp(identifier, otp, purpose)', 'output': '{"verification_token": str}', 'auth': 'No'},
                {'method': 'POST', 'url': '/api/auth/device', 'purpose': 'Update FCM token and device data', 'input': 'UserDeviceSerializer', 'service': 'UserDeviceService().register_device(user, validated_data)', 'output': 'UserDeviceSerializer data', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/auth/me', 'purpose': 'Returns authenticated user basic data', 'input': 'None', 'service': 'UserSerializer(request.user)', 'output': 'UserSerializer data', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/users/profile', 'purpose': 'Fetches user full profile', 'input': 'None', 'service': 'UserProfileSerializer(user.profile)', 'output': 'UserProfileSerializer data', 'auth': 'JWT Required'},
                {'method': 'PUT', 'url': '/api/users/profile', 'purpose': 'Updates user profile', 'input': 'UserProfileSerializer', 'service': 'UserProfileService().update_profile(user, validated_data)', 'output': 'UserProfileSerializer data', 'auth': 'JWT Required'},
                {'method': 'POST', 'url': '/api/users/kyc', 'purpose': 'Upload KYC documents', 'input': 'UserKYCSerializer', 'service': 'UserKYCService().submit_kyc(user, validated_data)', 'output': 'UserKYCSerializer data', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/users/kyc/status', 'purpose': 'Returns KYC verification status', 'input': 'None', 'service': 'UserKYCSerializer(user.kyc)', 'output': '{"status": "pending|approved|rejected"}', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/users/wallet', 'purpose': 'Display wallet balance and points', 'input': 'None', 'service': 'WalletService().get_wallet_balance(user)', 'output': '{"balance": str, "points": int}', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/users/analytics/usage-stats', 'purpose': 'Provides usage statistics', 'input': 'None', 'service': 'UserProfileService().get_user_analytics(user)', 'output': 'UserAnalyticsSerializer data', 'auth': 'JWT Required'}
            ],
            'stations': [
                {'method': 'GET', 'url': '/api/stations', 'purpose': 'Lists all active stations with real-time status', 'input': 'None', 'service': 'Station.objects.filter(is_active=True)', 'output': 'List of StationSerializer data', 'auth': 'No'},
                {'method': 'GET', 'url': '/api/stations/{sn}', 'purpose': 'Returns detailed station data', 'input': 'None', 'service': 'Station.objects.get(serial_number=sn)', 'output': 'StationDetailSerializer data', 'auth': 'No'},
                {'method': 'GET', 'url': '/api/stations/nearby', 'purpose': 'Fetches stations within radius', 'input': 'lat, lng, radius params', 'service': 'StationService().get_nearby_stations(lat, lng, radius)', 'output': 'List of StationSerializer data', 'auth': 'No'},
                {'method': 'POST', 'url': '/api/stations/{sn}/favorite', 'purpose': 'Adds station to favorites', 'input': 'None', 'service': 'StationService().add_favorite(user, station)', 'output': '{"message": "Added to favorites"}', 'auth': 'JWT Required'},
                {'method': 'DELETE', 'url': '/api/stations/{sn}/favorite', 'purpose': 'Removes station from favorites', 'input': 'None', 'service': 'StationService().remove_favorite(user, station)', 'output': '{"message": "Removed from favorites"}', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/stations/favorites', 'purpose': 'Returns user favorite stations', 'input': 'None', 'service': 'StationService().get_user_favorites(user)', 'output': 'List of StationSerializer data', 'auth': 'JWT Required'},
                {'method': 'POST', 'url': '/api/stations/{sn}/report-issue', 'purpose': 'Report station issues', 'input': 'IssueReportSerializer', 'service': 'StationService().report_issue(user, station, issue_data)', 'output': '{"report_id": str}', 'auth': 'JWT Required'}
            ],
            'notifications': [
                {'method': 'GET', 'url': '/api/notifications', 'purpose': 'Get user notifications', 'input': 'None', 'service': 'Notification.objects.filter(user=request.user)', 'output': 'List of NotificationSerializer data', 'auth': 'JWT Required'},
                {'method': 'PATCH', 'url': '/api/notifications/{id}', 'purpose': 'Mark notification as read', 'input': 'None', 'service': 'NotificationService().mark_as_read(notification)', 'output': 'NotificationSerializer data', 'auth': 'JWT Required'},
                {'method': 'POST', 'url': '/api/notifications/mark-all-read', 'purpose': 'Mark all notifications as read', 'input': 'None', 'service': 'NotificationService().mark_all_as_read(user)', 'output': '{"message": "All marked as read"}', 'auth': 'JWT Required'},
                {'method': 'DELETE', 'url': '/api/notifications/{id}', 'purpose': 'Delete notification', 'input': 'None', 'service': 'notification.delete()', 'output': '{"message": "Deleted"}', 'auth': 'JWT Required'}
            ],
            'payments': [
                {'method': 'GET', 'url': '/api/payments/transactions', 'purpose': 'Lists wallet transactions', 'input': 'None', 'service': 'TransactionService().get_user_transactions(user)', 'output': 'List of TransactionSerializer data', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/payments/packages', 'purpose': 'Lists rental packages', 'input': 'None', 'service': 'RentalPackage.objects.filter(is_active=True)', 'output': 'List of RentalPackageSerializer data', 'auth': 'No'},
                {'method': 'GET', 'url': '/api/payments/methods', 'purpose': 'Returns active payment gateways', 'input': 'None', 'service': 'PaymentMethod.objects.filter(is_active=True)', 'output': 'List of PaymentMethodSerializer data', 'auth': 'No'},
                {'method': 'POST', 'url': '/api/payments/wallet/topup-intent', 'purpose': 'Creates payment intent for wallet top-up', 'input': 'TopupIntentCreateSerializer', 'service': 'PaymentIntentService().create_topup_intent(user, amount, payment_method_id)', 'output': '{"intent_id": str, "payment_url": str}', 'auth': 'JWT Required'},
                {'method': 'POST', 'url': '/api/payments/verify-topup', 'purpose': 'Validates top-up payment and updates wallet', 'input': 'VerifyTopupSerializer', 'service': 'PaymentIntentService().verify_topup_payment(intent_id, gateway_reference)', 'output': '{"status": str, "balance": str}', 'auth': 'JWT Required'},
                {'method': 'POST', 'url': '/api/payments/calculate-options', 'purpose': 'Calculate payment options for scenarios', 'input': 'CalculatePaymentOptionsSerializer', 'service': 'PaymentCalculationService().calculate_payment_options(user, scenario, amount)', 'output': 'PaymentOptionsResponseSerializer data', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/payments/status/{intent_id}', 'purpose': 'Returns payment intent status', 'input': 'None', 'service': 'PaymentIntentService().get_payment_status(intent_id)', 'output': 'PaymentStatusSerializer data', 'auth': 'JWT Required'}
            ],
            'points': [
                {'method': 'GET', 'url': '/api/points/history', 'purpose': 'Lists points transactions', 'input': 'None', 'service': 'PointsService().get_user_points_history(user)', 'output': 'List of PointsTransactionSerializer data', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/points/summary', 'purpose': 'Returns points overview', 'input': 'None', 'service': 'PointsService().get_points_summary(user)', 'output': '{"current_points": int, "total_earned": int}', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/referrals/my-code', 'purpose': 'Returns user referral code', 'input': 'None', 'service': 'ReferralService().get_user_referral_code(user)', 'output': '{"referral_code": str}', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/referrals/validate', 'purpose': 'Validates referral code', 'input': 'code param', 'service': 'ReferralService().validate_referral_code(code)', 'output': '{"valid": bool, "referrer": str}', 'auth': 'No'},
                {'method': 'POST', 'url': '/api/referrals/claim', 'purpose': 'Claims referral rewards', 'input': 'ReferralClaimSerializer', 'service': 'ReferralService().claim_referral(user, referral_code)', 'output': '{"points_awarded": int}', 'auth': 'JWT Required'}
            ],
            'rentals': [
                {'method': 'POST', 'url': '/api/rentals/start', 'purpose': 'Initiates rental session', 'input': 'StartRentalSerializer', 'service': 'RentalService().start_rental(user, station_sn, package_id)', 'output': 'RentalSerializer data', 'auth': 'JWT Required'},
                {'method': 'POST', 'url': '/api/rentals/{rental_id}/cancel', 'purpose': 'Cancels active rental', 'input': 'None', 'service': 'RentalService().cancel_rental(user, rental_id)', 'output': '{"message": "Rental cancelled"}', 'auth': 'JWT Required'},
                {'method': 'POST', 'url': '/api/rentals/{rental_id}/extend', 'purpose': 'Extends rental duration', 'input': 'ExtendRentalSerializer', 'service': 'RentalService().extend_rental(user, rental_id, additional_time)', 'output': 'RentalSerializer data', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/rentals/active', 'purpose': 'Returns current active rental', 'input': 'None', 'service': 'RentalService().get_active_rental(user)', 'output': 'RentalSerializer data or null', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/rentals/history', 'purpose': 'Returns rental history', 'input': 'page, page_size params', 'service': 'RentalService().get_user_rental_history(user)', 'output': 'Paginated RentalSerializer data', 'auth': 'JWT Required'},
                {'method': 'POST', 'url': '/api/rentals/{id}/pay-due', 'purpose': 'Pays outstanding rental dues', 'input': 'PayDueSerializer', 'service': 'RentalPaymentService().pay_rental_due(user, rental, payment_breakdown)', 'output': '{"payment_status": str}', 'auth': 'JWT Required'}
            ],
            'social': [
                {'method': 'GET', 'url': '/api/social/leaderboard', 'purpose': 'Returns user rankings', 'input': 'me param optional', 'service': 'SocialService().get_leaderboard(include_user=me)', 'output': 'List of LeaderboardSerializer data', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/social/achievements', 'purpose': 'Returns user achievements', 'input': 'None', 'service': 'SocialService().get_user_achievements(user)', 'output': 'List of AchievementSerializer data', 'auth': 'JWT Required'}
            ],
            'promotions': [
                {'method': 'POST', 'url': '/api/promotions/coupons/apply', 'purpose': 'Apply coupon code', 'input': 'CouponApplySerializer', 'service': 'PromotionService().apply_coupon(user, coupon_code)', 'output': '{"points_awarded": int}', 'auth': 'JWT Required'},
                {'method': 'GET', 'url': '/api/promotions/coupons/my', 'purpose': 'Returns user coupons', 'input': 'None', 'service': 'PromotionService().get_user_coupons(user)', 'output': 'List of UserCouponSerializer data', 'auth': 'JWT Required'}
            ],
            'content': [
                {'method': 'GET', 'url': '/api/content/terms-of-service', 'purpose': 'Returns terms of service', 'input': 'None', 'service': 'ContentService().get_terms_of_service()', 'output': 'ContentSerializer data', 'auth': 'No'},
                {'method': 'GET', 'url': '/api/content/privacy-policy', 'purpose': 'Returns privacy policy', 'input': 'None', 'service': 'ContentService().get_privacy_policy()', 'output': 'ContentSerializer data', 'auth': 'No'},
                {'method': 'GET', 'url': '/api/content/about', 'purpose': 'Returns about information', 'input': 'None', 'service': 'ContentService().get_about_info()', 'output': 'ContentSerializer data', 'auth': 'No'},
                {'method': 'GET', 'url': '/api/content/contact', 'purpose': 'Returns contact information', 'input': 'None', 'service': 'ContentService().get_contact_info()', 'output': 'ContentSerializer data', 'auth': 'No'},
                {'method': 'GET', 'url': '/api/content/faq', 'purpose': 'Returns FAQ content', 'input': 'None', 'service': 'ContentService().get_faq()', 'output': 'List of FAQSerializer data', 'auth': 'No'}
            ],
            'admin': [
                {'method': 'GET', 'url': '/api/admin/users', 'purpose': 'Lists all users (paginated)', 'input': 'page, page_size params', 'service': 'AdminUserService().get_all_users()', 'output': 'Paginated UserSerializer data', 'auth': 'Admin Required'},
                {'method': 'GET', 'url': '/api/admin/stations', 'purpose': 'Lists all stations (paginated)', 'input': 'page, page_size params', 'service': 'AdminStationService().get_all_stations()', 'output': 'Paginated StationSerializer data', 'auth': 'Admin Required'},
                {'method': 'GET', 'url': '/api/admin/analytics/dashboard', 'purpose': 'Returns dashboard metrics', 'input': 'None', 'service': 'AdminAnalyticsService().get_dashboard_metrics()', 'output': 'DashboardMetricsSerializer data', 'auth': 'Admin Required'}
            ]
        }
        
        # Get endpoints for this app
        app_endpoints = endpoint_mappings.get(app_name, [])
        
        if app_endpoints:
            content.append("## 🎆 Suggested API Endpoints (for AI view generation)")
            content.append("")
            content.append("*Based on Features TOC mapping and available code structure*")
            content.append("")
            
            for endpoint in app_endpoints:
                content.append(f"### `{endpoint['method']} {endpoint['url']}`")
                content.append(f"**Purpose**: {endpoint['purpose']}")
                content.append(f"**Input**: {endpoint['input']}")
                content.append(f"**Service**: {endpoint['service']}")
                content.append(f"**Output**: {endpoint['output']}")
                content.append(f"**Auth**: {endpoint['auth']}")
                content.append("")
        else:
            # Fallback to integration patterns for apps not in mapping
            content.extend(self._generate_integration_patterns(app_doc))
        
        return content
    def _generate_integration_patterns(self, app_doc: Dict[str, Any]) -> List[str]:
        """Generate integration patterns as fallback for unmapped apps."""
        content = []
        app_name = app_doc['app_name']
        
        content.append("## 🔗 Integration Patterns (for AI view generation)")
        content.append("")
        content.append("*Available services, serializers, and common Django patterns for this app*")
        content.append("")
        
        # Extract services and serializers from analysis
        services = []
        serializers = []
        
        for filename, analysis in app_doc['analyzed_files'].items():
            if filename == 'services.py':
                services = [cls for cls in analysis['classes'] 
                           if 'Service' in cls['name']]
            elif filename == 'serializers.py':
                serializers = [cls for cls in analysis['classes'] 
                              if 'Serializer' in cls['name'] and cls['name'] != 'Meta']
        
        # Show service-serializer relationships
        if services and serializers:
            content.append("### 🔄 Service-Serializer Integration Patterns")
            content.append("")
            
            for service in services[:3]:  # Limit to avoid clutter
                content.append(f"**{service['name']}** can work with:")
                
                # Find related serializers (heuristic based on naming)
                service_domain = service['name'].replace('Service', '').lower()
                related_serializers = [s for s in serializers 
                                     if service_domain in s['name'].lower()]
                
                if related_serializers:
                    for serializer in related_serializers[:3]:
                        content.append(f"- `{serializer['name']}` for data validation")
                else:
                    content.append(f"- Any appropriate serializer for data validation")
                
                content.append("")
        
        # Show common view patterns
        content.append("### 🎨 Common View Patterns")
        content.append("")
        content.append("**Typical Django REST patterns for this app:**")
        content.append("- Use service classes for business logic")
        content.append("- Validate input with appropriate serializers")
        content.append("- Apply authentication where needed")
        content.append("- Handle pagination for list views")
        content.append("- Return appropriate HTTP status codes")
        content.append("")
        
        return content
    
    def _generate_ai_optimized_file_docs(self, filename: str, analysis: Dict[str, Any]) -> List[str]:
        """Generate AI-optimized documentation for views/urls generation."""
        content = []
        
        content.append(f"## {filename}")
        content.append("")
        
        if filename == 'models.py':
            content.extend(self._generate_models_for_ai(analysis))
        elif filename == 'serializers.py':
            content.extend(self._generate_serializers_for_ai(analysis))
        elif filename == 'services.py':
            content.extend(self._generate_services_for_ai(analysis))
        elif filename == 'tasks.py':
            content.extend(self._generate_tasks_for_ai(analysis))
        elif filename == 'permissions.py':
            content.extend(self._generate_permissions_for_ai(analysis))
        
        return content
    
    def _generate_models_for_ai(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate AI-optimized models documentation for view generation."""
        content = []
        
        django_models = [cls for cls in analysis['classes'] 
                        if any('Model' in base for base in cls['base_classes'])]
        
        if django_models:
            content.append("**🏗️ Available Models (for view generation):**")
            content.append("")
            
            for model in django_models:
                # Skip Meta classes
                if model['name'] == 'Meta':
                    continue
                    
                content.append(f"### `{model['name']}`")
                if model['docstring']:
                    content.append(f"*{model['docstring']}*")
                
                # Extract field information from class variables
                fields = [var for var in model['class_variables'] 
                         if 'models.' in var['value'] and 'Field' in var['value']]
                
                if fields:
                    content.append("\n**Key Fields:**")
                    for field in fields:
                        field_type = self._extract_field_type(field['value'])
                        content.append(f"- `{field['name']}`: {field_type}")
                
                content.append("")
        
        return content
    
    def _generate_serializers_for_ai(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate AI-optimized serializers documentation for view generation."""
        content = []
        
        serializers = [cls for cls in analysis['classes'] 
                      if any('Serializer' in base for base in cls['base_classes'])]
        
        if serializers:
            content.append("**📝 Available Serializers (for view generation):**")
            content.append("")
            
            for serializer in serializers:
                if serializer['name'] == 'Meta':
                    continue
                    
                content.append(f"### `{serializer['name']}`")
                if serializer['docstring']:
                    content.append(f"*{serializer['docstring']}*")
                
                # Extract validation methods
                validation_methods = [method for method in serializer['methods'] 
                                    if method['name'].startswith('validate')]
                
                if validation_methods:
                    content.append("\n**Validation Methods:**")
                    for method in validation_methods:
                        content.append(f"- `{method['name']}()`")
                
                content.append("")
        
        return content
    
    def _generate_services_for_ai(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate AI-optimized services documentation for view generation."""
        content = []
        
        services = [cls for cls in analysis['classes'] 
                   if 'Service' in cls['name'] or any('Service' in base for base in cls['base_classes'])]
        
        if services:
            content.append("**⚙️ Available Services (for view logic):**")
            content.append("")
            
            for service in services:
                content.append(f"### `{service['name']}`")
                if service['docstring']:
                    content.append(f"*{service['docstring']}*")
                
                # Show public methods (not private/protected)
                public_methods = [method for method in service['methods'] 
                                if not method['name'].startswith('_')]
                
                if public_methods:
                    content.append("\n**Available Methods:**")
                    for method in public_methods:
                        args = [arg['name'] for arg in method['args'] if arg['name'] not in ['self', 'cls']]
                        args_str = ', '.join(args)
                        return_type = f" -> {method['returns']}" if method['returns'] else ""
                        content.append(f"- `{method['name']}({args_str}){return_type}`")
                        if method['docstring']:
                            desc = method['docstring'].split('\n')[0]  # First line only
                            content.append(f"  - *{desc}*")
                
                content.append("")
        
        return content
    
    def _generate_tasks_for_ai(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate AI-optimized tasks documentation for view generation."""
        content = []
        
        # Look for Celery tasks (functions with @shared_task decorator)
        tasks = [func for func in analysis['functions'] 
                if any('shared_task' in dec for dec in func['decorators'])]
        
        if tasks:
            content.append("**🔄 Available Background Tasks:**")
            content.append("")
            
            for task in tasks:
                args = [arg['name'] for arg in task['args'] if arg['name'] != 'self']
                args_str = ', '.join(args)
                content.append(f"- `{task['name']}({args_str})`")
                if task['docstring']:
                    desc = task['docstring'].split('\n')[0]  # First line only
                    content.append(f"  - *{desc}*")
            
            content.append("")
        
        return content
    
    def _generate_permissions_for_ai(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate AI-optimized permissions documentation for view generation."""
        content = []
        
        permissions = [cls for cls in analysis['classes'] 
                      if any('Permission' in base for base in cls['base_classes'])]
        
        if permissions:
            content.append("**🔒 Available Permissions (for view protection):**")
            content.append("")
            
            for perm in permissions:
                content.append(f"- `{perm['name']}`")
                if perm['docstring']:
                    content.append(f"  - *{perm['docstring']}*")
            
            content.append("")
        
        return content
    
    def _infer_app_purpose(self, app_name: str) -> str:
        """Infer the purpose of an app based on its name."""
        purposes = {
            'users': 'User management, authentication, profiles',
            'payments': 'Payment processing, wallets, transactions',
            'stations': 'Charging station management and IoT integration',
            'rentals': 'Power bank rental and return operations',
            'notifications': 'Push notifications and alerts system',
            'points': 'Gamification and rewards system',
            'promotions': 'Marketing campaigns and promotions',
            'social': 'Social features and user interactions',
            'content': 'Content management and static data',
            'admin': 'Administrative dashboard and controls',
            'common': 'Shared utilities and base components'
        }
        return purposes.get(app_name.lower(), f'{app_name.title()} app functionality')
    
    def _extract_field_type(self, field_value: str) -> str:
        """Extract simplified field type from Django field definition."""
        if 'ForeignKey' in field_value:
            return 'ForeignKey (relation)'
        elif 'OneToOneField' in field_value:
            return 'OneToOneField (relation)'
        elif 'ManyToManyField' in field_value:
            return 'ManyToManyField (relation)'
        elif 'CharField' in field_value:
            return 'CharField (text)'
        elif 'TextField' in field_value:
            return 'TextField (long text)'
        elif 'EmailField' in field_value:
            return 'EmailField (email)'
        elif 'URLField' in field_value:
            return 'URLField (url)'
        elif 'IntegerField' in field_value:
            return 'IntegerField (number)'
        elif 'DecimalField' in field_value:
            return 'DecimalField (decimal)'
        elif 'BooleanField' in field_value:
            return 'BooleanField (true/false)'
        elif 'DateTimeField' in field_value:
            return 'DateTimeField (datetime)'
        elif 'DateField' in field_value:
            return 'DateField (date)'
        elif 'JSONField' in field_value:
            return 'JSONField (json data)'
        else:
            return field_value.split('(')[0] if '(' in field_value else field_value
    
    def _format_arguments(self, args: List[Dict[str, Any]]) -> str:
        """Format function/method arguments for display."""
        formatted_args = []
        
        for arg in args:
            arg_str = arg['name']
            
            # Add type annotation
            if arg.get('annotation'):
                arg_str += f": {arg['annotation']}"
            
            # Add default value
            if arg.get('default'):
                arg_str += f" = {arg['default']}"
            
            formatted_args.append(arg_str)
        
        return ', '.join(formatted_args)
    
    def generate_app_documentation(self, app_name: str) -> str:
        """Generate complete documentation for an app."""
        print(f"📝 Generating documentation for '{app_name}' app...")
        
        # Analyze the app
        app_doc = self.analyze_app(app_name)
        
        # Generate markdown
        markdown_content = self.generate_markdown_documentation(app_doc)
        
        # Save to file
        output_file = self.api_dir / app_name / f"{app_name}_documentation.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"✅ Documentation saved to: {output_file}")
        
        return str(output_file)
    
    def generate_all_apps_documentation(self) -> List[str]:
        """Generate documentation for all available apps."""
        apps = self.get_available_apps()
        
        if not apps:
            print("❌ No Django apps found in the api directory!")
            return []
        
        print(f"📚 Found {len(apps)} apps: {', '.join(apps)}")
        
        generated_files = []
        
        for app_name in apps:
            try:
                output_file = self.generate_app_documentation(app_name)
                generated_files.append(output_file)
            except Exception as e:
                print(f"❌ Failed to generate documentation for '{app_name}': {str(e)}")
        
        return generated_files


def main():
    """Main entry point for the app documentation generator."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive documentation for Django apps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app_docs.py --dir users          # Generate docs for users app
  python app_docs.py --dir payments       # Generate docs for payments app  
  python app_docs.py --all                # Generate docs for all apps
  python app_docs.py --list               # List available apps
        """
    )
    
    parser.add_argument(
        '--dir', 
        type=str, 
        help='Generate documentation for specific app directory'
    )
    
    parser.add_argument(
        '--all', 
        action='store_true',
        help='Generate documentation for all available apps'
    )
    
    parser.add_argument(
        '--list', 
        action='store_true',
        help='List all available apps'
    )
    
    parser.add_argument(
        '--detailed', 
        action='store_true',
        help='Generate detailed documentation (default: AI-optimized)'
    )
    
    args = parser.parse_args()
    
    # Initialize generator
    try:
        generator = DjangoAppDocumentationGenerator(api_dir='api')
    except Exception as e:
        print(f"❌ Failed to initialize generator: {str(e)}")
        return 1
    
    # Handle list command
    if args.list:
        apps = generator.get_available_apps()
        if apps:
            print(f"📋 Available Django apps ({len(apps)}):")
            for app in apps:
                print(f"  - {app}")
        else:
            print("❌ No Django apps found!")
        return 0
    
    # Handle single app documentation
    if args.dir:
        try:
            output_file = generator.generate_app_documentation(args.dir)
            print(f"\n🎉 Documentation generation completed!")
            print(f"📄 Output: {output_file}")
            return 0
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return 1
    
    # Handle all apps documentation
    if args.all:
        try:
            output_files = generator.generate_all_apps_documentation()
            print(f"\n🎉 Documentation generation completed!")
            print(f"📄 Generated {len(output_files)} files:")
            for file_path in output_files:
                print(f"  - {file_path}")
            return 0
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return 1
    
    # No valid arguments provided
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())