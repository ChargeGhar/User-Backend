#!/usr/bin/env python3
"""
API Format Extractor
Extracts and displays request/response formats from API documentation.

Usage:
    python extract_req.py [endpoint]  # Show formats for specific endpoint
    python extract_req.py --list      # List all available endpoints
"""

import re
import sys
from pathlib import Path

class APIFormatExtractor:
    """Extracts request/response formats from markdown API docs."""
    
    def __init__(self, md_file_path: str = "payment_rental_req.md"):
        self.md_file_path = Path(md_file_path)
        self.endpoints = []
        
        # Patterns to match sections and content
        self.endpoint_pattern = re.compile(r'### \*\*Endpoint\*\*\s*`([^`]+)`')
        self.method_pattern = re.compile(r'^### \*\*(GET|POST|PUT|DELETE|PATCH)\*\*', re.MULTILINE)
        self.request_pattern = re.compile(r'### \*\*Request\*\*(.*?)(?=###|\Z)', re.DOTALL)
        self.response_pattern = re.compile(r'### \*\*Response\*\*(.*?)(?=###|\Z)', re.DOTALL)
        self.json_pattern = re.compile(r'```(?:json)?\n(.*?)\n```', re.DOTALL)
        self.section_pattern = re.compile(r'## (.+?)(?=\n## |\Z)', re.DOTALL)
    
    def parse_file(self) -> None:
        """Parse the markdown file to extract API formats."""
        try:
            content = self.md_file_path.read_text(encoding='utf-8')
        except FileNotFoundError:
            print(f"Error: File not found - {self.md_file_path}")
            return
            
        # Split into sections (each starting with ##)
        sections = self.section_pattern.findall(content)
        
        # Dictionary to store unique endpoints by method and path
        unique_endpoints = {}
        
        for section in sections:
            # Find endpoint and method
            endpoint_match = self.endpoint_pattern.search(section)
            if not endpoint_match:
                continue
                
            # Extract the endpoint line
            endpoint_line = endpoint_match.group(1).strip()
            
            # Default to GET if no method specified
            method = 'GET'
            endpoint = endpoint_line
            
            # Check if method is specified in the endpoint
            for http_method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                if endpoint_line.upper().startswith(f"{http_method} "):
                    method = http_method
                    endpoint = endpoint_line[len(http_method):].strip()
                    break
            
            # Extract request and response sections
            request_section = self.request_pattern.search(section)
            response_section = self.response_pattern.search(section)
            
            # Extract all JSON blocks from each section
            request = self.json_pattern.findall(request_section.group(1)) if request_section else []
            response = self.json_pattern.findall(response_section.group(1)) if response_section else []
            
            # Create a unique key for the endpoint (method + path)
            endpoint_key = f"{method.upper()} {endpoint}"
            
            # Only add if we don't have this exact endpoint yet
            if endpoint_key not in unique_endpoints:
                unique_endpoints[endpoint_key] = {
                    'method': method.upper(),
                    'endpoint': endpoint,
                    'request': request,
                    'response': response
                }
        
        # Convert the dictionary values to the endpoints list
        self.endpoints = list(unique_endpoints.values())

def print_formats(method: str, endpoint: str, request: list, response: list) -> None:
    """Print the request and response formats in a clean way."""
    # Colors for different methods
    colors = {
        'GET': '\033[92m',    # Green
        'POST': '\033[94m',   # Blue
        'PUT': '\033[33m',    # Yellow
        'DELETE': '\033[91m', # Red
        'PATCH': '\033[95m'   # Purple
    }
    
    method_color = colors.get(method, '\033[0m')
    
    # Print method and endpoint with color
    print(f"\n{method_color}{method}\033[0m {endpoint}")
    print("=" * 80)
    
    # Print request
    if request:
        print("\n\033[1mREQUEST\033[0m")
        print("-" * 8)
        for i, req in enumerate(request, 1):
            if i > 1:
                print("\n--- OR ---\n")
            print(f"```json\n{req}\n```")
    
    # Print response
    if response:
        print("\n\033[1mRESPONSE\033[0m")
        print("-" * 9)
        for i, resp in enumerate(response, 1):
            if i > 1:
                print("\n--- OR ---\n")
            print(f"```json\n{resp}\n```")
    
    print("\n" + "=" * 80 + "\n")

def main():
    """Main function for command-line usage."""
    import sys
    
    # Get endpoint from command line or use None for list
    endpoint_query = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else None
    
    # Check for --list flag
    list_mode = '--list' in sys.argv
    if list_mode and endpoint_query:
        endpoint_query = endpoint_query.replace('--list', '').strip()
    
    extractor = APIFormatExtractor()
    extractor.parse_file()
    
    if not extractor.endpoints:
        print("No API endpoints found in the markdown file.")
        return
    
    # Sort endpoints by method and then by endpoint path
    sorted_endpoints = sorted(
        extractor.endpoints,
        key=lambda x: (x['method'], x['endpoint'])
    )
    
    # List all endpoints
    if list_mode or not endpoint_query:
        print("\nAvailable Endpoints:")
        print("=" * 80)
        for i, ep in enumerate(sorted_endpoints, 1):
            print(f"{i:2d}. {ep['method']} {ep['endpoint']}")
        print("\nUse: python extract_req.py [endpoint] to view formats")
        return
    
    # Find matching endpoints
    matches = [
        ep for ep in extractor.endpoints 
        if endpoint_query.lower() in f"{ep['method']} {ep['endpoint']}".lower()
    ]
    
    if not matches:
        print(f"No endpoints found matching: {endpoint_query}")
        return
    
    # Print formats for all matching endpoints
    for ep in matches:
        print_formats(
            ep['method'], 
            ep['endpoint'], 
            ep['request'], 
            ep['response']
        )

if __name__ == "__main__":
    main()