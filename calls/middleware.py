"""
Custom middleware for handling dashboard API access
"""

class DashboardAuthenticationMiddleware:
    """
    Middleware to bypass authentication for dashboard endpoints
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if this is a dashboard API request
        if self.is_dashboard_api_request(request):
            # Skip authentication for dashboard requests
            request._dont_enforce_csrf_checks = True
        
        response = self.get_response(request)
        return response

    def is_dashboard_api_request(self, request):
        """Check if the request is for dashboard API endpoints"""
        dashboard_paths = [
            '/api/dashboard/',
            '/calls/api/dashboard/',
            '/api/simple-dashboard/',
            '/calls/api/simple-dashboard/',
        ]
        
        return any(request.path.startswith(path) for path in dashboard_paths)
