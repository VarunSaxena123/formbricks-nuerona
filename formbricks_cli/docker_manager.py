import subprocess
import sys
import time
from pathlib import Path
import docker
from rich.console import Console

console = Console()

class DockerManager:
    def __init__(self):
        self.project_dir = Path(__file__).parent.parent
        self.docker_compose_path = self.project_dir / "docker-compose.yml"
        # Full path to docker.exe for Windows
        self.docker_path = r"C:\Program Files\Docker\Docker\resources\bin\docker.exe"
        
    def start_services(self):
        """Start Formbricks services using docker-compose"""
        try:
            # Check if Docker is running
            client = docker.from_env()
            client.ping()
        except:
            console.print("[red]Docker is not running. Please start Docker Desktop.[/red]")
            return False
        
        try:
            # Pull and start services
            console.print("[dim]Pulling latest Formbricks image...[/dim]")
            subprocess.run(
                [self.docker_path, "compose", "-f", str(self.docker_compose_path), "pull"],
                capture_output=True
            )
            
            console.print("[dim]Starting services...[/dim]")
            result = subprocess.run(
                [self.docker_path, "compose", "-f", str(self.docker_compose_path), "up", "-d"],
                capture_output=True,
                text=True
            )
            
            # Wait for services to be ready
            console.print("[dim]Waiting for services to be ready...[/dim]")
            time.sleep(30)  # Give time for initialization
            
            return True
            
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error starting services: {e.stderr}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            return False
    
    def stop_services(self):
        """Stop and clean up services"""
        try:
            # Stop and remove containers
            subprocess.run(
                [self.docker_path, "compose", "-f", str(self.docker_compose_path), "down", "-v"],
                capture_output=True
            )
            
            # Clean up volumes (optional)
            subprocess.run(
                [self.docker_path, "system", "prune", "-f"],
                capture_output=True
            )
            
            return True
            
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error stopping services: {e.stderr}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            return False
    
    def check_services_status(self):
        """Check if services are running"""
        try:
            result = subprocess.run(
                [self.docker_path, "compose", "-f", str(self.docker_compose_path), "ps"],
                capture_output=True,
                text=True
            )
            return "formbricks" in result.stdout
        except:
            return False