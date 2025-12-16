import typer
import traceback
from rich.console import Console
from rich.panel import Panel
from formbricks_cli.commands import (
    up_command,
    down_command,
    generate_command,
    seed_command
)
from formbricks_cli.utils import validate_environment

app = typer.Typer(
    help="Formbricks Challenge CLI Tool",
    add_completion=False,
    no_args_is_help=True
)
console = Console()

@app.command(name="formbricks")
def formbricks_main(
    action: str = typer.Argument(
        ...,
        help="Action to perform: up, down, generate, seed",
        show_default=False
    )
):
    """Main command for Formbricks operations
    
    Commands:
      up       - Start Formbricks locally using Docker
      down     - Stop and clean up Formbricks instance
      generate - Generate realistic data using LLM
      seed     - Seed data using Formbricks APIs
    """
    console.print(Panel.fit(
        f"[bold blue]Formbricks Challenge CLI[/bold blue]\n"
        f"Action: [cyan]{action}[/cyan]",
        border_style="blue"
    ))
    
    try:
        if action == "up":
            up_command()
        elif action == "down":
            down_command()
        elif action == "generate":
            generate_command()
        elif action == "seed":
            # Validate environment before seeding
            if not validate_environment():
                console.print("[yellow]Please set up your environment variables first[/yellow]")
                console.print("1. Run: python main.py formbricks up")
                console.print("2. Complete Formbricks setup at http://localhost:3000")
                console.print("3. Get API key from Settings → API Keys")
                console.print("4. Update .env file with FORMBRICKS_API_KEY")
                raise typer.Exit(1)
            seed_command()
        else:
            console.print(f"[red]Error: Unknown action '{action}'[/red]")
            console.print("Available actions: up, down, generate, seed")
            raise typer.Exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[dim]" + traceback.format_exc() + "[/dim]")
        raise typer.Exit(1)

@app.command(name="version")
def version():
    """Show version information"""
    console.print("[bold blue]Formbricks Challenge CLI v1.0.0[/bold blue]")

@app.command(name="status")
def status():
    """Check Formbricks status"""
    from formbricks_cli.docker_manager import DockerManager
    docker_manager = DockerManager()
    
    if docker_manager.check_services_status():
        console.print("[green]✓ Formbricks is running[/green]")
        console.print("   Access at: http://localhost:3000")
    else:
        console.print("[yellow]Formbricks is not running[/yellow]")
        console.print("   Start with: python main.py formbricks up")

if __name__ == "__main__":
    app()