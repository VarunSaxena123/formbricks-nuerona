"""
Utility functions for the Formbricks Challenge CLI
"""

import json
import yaml
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import hashlib
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()

def load_config(config_path: str = "config.yaml") -> Dict:
    """Load configuration from YAML file"""
    config_file = Path(config_path)
    if not config_file.exists():
        return {}
    
    with open(config_file, 'r') as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLerror as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            return {}

def save_json(data: Any, filepath: str) -> bool:
    """Save data to JSON file"""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        console.print(f"[red]Error saving to {filepath}: {e}[/red]")
        return False

def load_json(filepath: str) -> Any:
    """Load data from JSON file"""
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading {filepath}: {e}[/red]")
        return None

def validate_environment() -> bool:
    """Validate required environment variables"""
    required_vars = [
        'FORMBRICKS_URL',
        'FORMBRICKS_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        console.print(f"[yellow]Warning: Missing environment variables: {', '.join(missing_vars)}[/yellow]")
        console.print("Please set them in your .env file")
        return False
    
    return True

def format_timestamp(timestamp: Optional[str] = None) -> str:
    """Format timestamp for display"""
    if not timestamp:
        return "N/A"
    
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp

def generate_id(prefix: str = "id") -> str:
    """Generate a unique ID"""
    timestamp = datetime.now().isoformat()
    hash_input = f"{prefix}{timestamp}{os.urandom(16).hex()}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:12]

def display_data_summary(data_type: str, data: List[Dict]) -> None:
    """Display summary of generated/seeded data"""
    table = Table(title=f"{data_type.capitalize()} Summary", show_header=True, header_style="bold magenta")
    
    if data_type == "surveys":
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Questions", justify="right")
        table.add_column("Status", style="blue")
        
        for item in data:
            table.add_row(
                item.get("id", "N/A"),
                item.get("name", "Unnamed"),
                item.get("type", "web"),
                str(len(item.get("questions", []))),
                item.get("status", "unknown")
            )
    
    elif data_type == "users":
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Email")
        table.add_column("Role", style="yellow")
        table.add_column("Last Login")
        
        for item in data:
            table.add_row(
                item.get("id", "N/A"),
                item.get("name", "Anonymous"),
                item.get("email", "N/A"),
                item.get("role", "user"),
                format_timestamp(item.get("last_login"))
            )
    
    elif data_type == "responses":
        table.add_column("ID", style="cyan")
        table.add_column("Survey ID", style="green")
        table.add_column("User ID", style="yellow")
        table.add_column("Submitted")
        
        for item in data:
            table.add_row(
                item.get("id", "N/A"),
                item.get("survey_id", "N/A"),
                item.get("user_id", "Anonymous"),
                format_timestamp(item.get("created_at"))
            )
    
    console.print(table)

def check_docker_installed() -> bool:
    """Check if Docker is installed and running"""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception as e:
        console.print(f"[red]Docker not available: {e}[/red]")
        return False

def ensure_directory(directory: str) -> bool:
    """Ensure directory exists"""
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        console.print(f"[red]Error creating directory {directory}: {e}[/red]")
        return False

def clean_generated_data() -> bool:
    """Clean up generated data files"""
    data_dir = Path("generated_data")
    if not data_dir.exists():
        return True
    
    try:
        for file in data_dir.glob("*.json"):
            file.unlink()
        data_dir.rmdir()
        console.print("[green]Cleaned generated data[/green]")
        return True
    except Exception as e:
        console.print(f"[yellow]Warning: Could not clean generated data: {e}[/yellow]")
        return False

def retry_operation(operation, max_retries: int = 3, delay: float = 1.0):
    """Retry an operation with exponential backoff"""
    import time
    
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            console.print(f"[yellow]Retry {attempt + 1}/{max_retries} after error: {e}[/yellow]")
            time.sleep(delay * (2 ** attempt))  # Exponential backoff

class APIError(Exception):
    """Custom exception for API errors"""
    pass

def validate_survey_structure(survey: Dict) -> bool:
    """Validate survey structure"""
    required_fields = ["name", "type", "questions"]
    for field in required_fields:
        if field not in survey:
            console.print(f"[red]Missing required field in survey: {field}[/red]")
            return False
    
    if not isinstance(survey.get("questions"), list):
        console.print("[red]Survey questions must be a list[/red]")
        return False
    
    return True