import requests
import time
import uuid
from typing import List, Dict, Any, Optional
import os
import json
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress
import logging

load_dotenv()
console = Console()
logger = logging.getLogger(__name__)

class APISeeder:
    """Formbricks API seeder - handles API limitations gracefully"""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.getenv("FORMBRICKS_URL", "http://localhost:3000")
        self.api_key = api_key or os.getenv("FORMBRICKS_API_KEY")
        
        if not self.api_key:
            raise ValueError("FORMBRICKS_API_KEY environment variable is required")
        
        # Management API headers
        self.management_headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Try to get environment ID from existing surveys
        self.environment_id = self._discover_environment_id()
        
        if not self.environment_id:
            console.print("[yellow]⚠ Could not auto-discover environment ID[/yellow]")
            console.print("[yellow]We'll try alternative approaches...[/yellow]")
    
    def _discover_environment_id(self) -> Optional[str]:
        """Try to discover environment ID from existing data"""
        try:
            # First, try to get existing surveys to extract environment info
            response = requests.get(
                f"{self.base_url}/api/v1/management/surveys",
                headers=self.management_headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                console.print(f"[green]✓ Found surveys API endpoint[/green]")
                
                # Try to extract environment ID from survey data
                if isinstance(data, dict) and "data" in data:
                    surveys = data["data"]
                    if surveys and len(surveys) > 0:
                        # Check if surveys have environmentId field
                        first_survey = surveys[0]
                        if "environmentId" in first_survey:
                            return first_survey["environmentId"]
                
                # If we have surveys but no environmentId, use a default
                console.print("[yellow]⚠ No environmentId in survey data, using default[/yellow]")
                return "default"
            
        except Exception as e:
            console.print(f"[dim]Error discovering environment: {e}[/dim]")
        
        return None
    
    def test_connection(self) -> bool:
        """Test connection to Formbricks"""
        try:
            # Check if Formbricks is running
            response = requests.get(self.base_url, timeout=5)
            if response.status_code == 200:
                console.print("[green]✓ Formbricks is running[/green]")
                
                # Test API endpoint
                api_response = requests.get(
                    f"{self.base_url}/api/v1/management/surveys",
                    headers=self.management_headers,
                    timeout=5
                )
                
                if api_response.status_code == 200:
                    console.print("[green]✓ Surveys API endpoint is accessible[/green]")
                    return True
                else:
                    console.print(f"[yellow]⚠ Surveys API returned: {api_response.status_code}[/yellow]")
                    console.print("[yellow]We'll try to proceed anyway...[/yellow]")
                    return True
            else:
                console.print("[red]✗ Formbricks is not running[/red]")
                return False
                
        except requests.exceptions.ConnectionError:
            console.print("[red]✗ Cannot connect to Formbricks[/red]")
            return False
        except Exception as e:
            console.print(f"[red]✗ Connection test failed: {e}[/red]")
            return False
    
    def create_users(self, users_data: List[Dict]) -> List[Dict]:
        """Prepare users - Formbricks doesn't have direct user creation API"""
        console.print("[yellow]Note: User creation via API is not available in Formbricks[/yellow]")
        console.print("[yellow]Users will be represented by their email addresses in responses[/yellow]")
        
        prepared_users = []
        for user_data in users_data:
            # Generate a consistent ID for this user
            user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_data["email"]))
            user_data["api_user_id"] = user_id
            prepared_users.append(user_data)
            
            console.print(f"[green]✓ Prepared user: {user_data['name']}[/green]")
        
        return prepared_users
    
    def create_surveys(self, surveys_data: List[Dict]) -> List[Dict]:
        """Create surveys via Formbricks API with multiple fallback strategies"""
        created_surveys = []
        
        for survey_data in surveys_data:
            try:
                endpoint = f"{self.base_url}/api/v1/management/surveys"
                
                # Format questions SIMPLIFIED
                questions = []
                for i, q in enumerate(survey_data.get("questions", []), 1):
                    question = {
                        "id": q.get("id", f"q{i}"),
                        "type": q.get("type", "text"),
                        "headline": q.get("headline", f"Question {i}"),
                        "required": q.get("required", False)
                    }
                    
                    # Add minimal type-specific fields
                    if q.get("type") == "rating":
                        question["range"] = q.get("range", 5)
                        question["scale"] = "number"
                    elif q.get("type") == "multipleChoice":
                        question["choices"] = q.get("choices", ["Option 1", "Option 2"])
                    
                    questions.append(question)
                
                # Try different payload strategies
                payload_strategies = []
                
                # Strategy 1: With environmentId if we have it
                if self.environment_id:
                    payload_strategies.append({
                        "environmentId": self.environment_id,
                        "name": survey_data["name"],
                        "type": "link",
                        "questions": questions,
                        "welcomeCard": {"enabled": False},
                        "thankYouCard": {"enabled": False}
                    })
                
                # Strategy 2: Without environmentId (might work)
                payload_strategies.append({
                    "name": survey_data["name"],
                    "type": "link",
                    "questions": questions,
                    "welcomeCard": {"enabled": False},
                    "thankYouCard": {"enabled": False}
                })
                
                # Strategy 3: Minimal payload
                payload_strategies.append({
                    "name": survey_data["name"],
                    "type": "link",
                    "questions": [questions[0]] if questions else []  # Just one question
                })
                
                created = False
                for strategy_num, payload in enumerate(payload_strategies, 1):
                    console.print(f"[dim]Trying strategy {strategy_num} for {survey_data['name']}[/dim]")
                    
                    try:
                        response = requests.post(
                            endpoint,
                            headers=self.management_headers,
                            json=payload,
                            timeout=30
                        )
                        
                        if response.status_code in [200, 201]:
                            result = response.json()
                            survey_id = result.get("id") or f"survey_{len(created_surveys)}"
                            
                            survey_info = {
                                "id": survey_id,
                                "name": survey_data["name"],
                                "questions": questions,
                                "api_success": True,
                                "response_data": result
                            }
                            created_surveys.append(survey_info)
                            console.print(f"[green]✓ Created survey: {survey_data['name']}[/green]")
                            created = True
                            break
                        else:
                            console.print(f"[dim]Strategy {strategy_num} failed: {response.status_code}[/dim]")
                            
                    except Exception as e:
                        console.print(f"[dim]Strategy {strategy_num} error: {e}[/dim]")
                        continue
                
                if not created:
                    console.print(f"[yellow]⚠ Could not create survey via API: {survey_data['name']}[/yellow]")
                    console.print("[yellow]Creating mock survey record for response testing[/yellow]")
                    
                    # Create mock survey for response testing
                    survey_info = {
                        "id": f"mock_survey_{len(created_surveys)}",
                        "name": survey_data["name"],
                        "questions": questions,
                        "api_success": False,
                        "response_data": {}
                    }
                    created_surveys.append(survey_info)
                    
            except Exception as e:
                console.print(f"[red]Error with survey {survey_data.get('name')}: {e}[/red]")
                logger.exception("Survey creation error")
        
        return created_surveys
    
    def submit_responses(self, responses_data: List[Dict], created_surveys: List[Dict]) -> List[Dict]:
        """Submit responses via Formbricks Client API"""
        created_responses = []
        
        # Filter to only surveys that were created via API
        api_surveys = [s for s in created_surveys if s.get("api_success", False)]
        
        if not api_surveys:
            console.print("[yellow]⚠ No surveys created via API, cannot submit responses[/yellow]")
            console.print("[yellow]Creating mock response records[/yellow]")
            
            # Create mock responses
            for response_data in responses_data:
                response_data["api_success"] = False
                response_data["submitted"] = False
                created_responses.append(response_data)
            
            return created_responses
        
        # Create mapping
        survey_map = {s["id"]: s for s in api_surveys}
        
        for response_data in responses_data:
            try:
                survey_id = response_data.get("survey_id")
                if survey_id not in survey_map:
                    console.print(f"[dim]Survey {survey_id} not in API-created surveys[/dim]")
                    continue
                
                survey = survey_map[survey_id]
                actual_survey_id = survey["id"]
                
                # Prepare response
                response_payload = {
                    "surveyId": actual_survey_id,
                    "responses": response_data.get("data", {}),
                    "finished": True,
                    "ttc": response_data.get("ttc", 30),
                    "userId": response_data.get("user_id", str(uuid.uuid4()))
                }
                
                # Try different endpoints
                endpoints = [
                    f"{self.base_url}/api/v1/client/responses",
                    f"{self.base_url}/api/v1/responses",
                ]
                
                submitted = False
                for endpoint in endpoints:
                    try:
                        response = requests.post(
                            endpoint,
                            json=response_payload,
                            timeout=30
                        )
                        
                        if response.status_code in [200, 201]:
                            response_data["api_success"] = True
                            response_data["submitted"] = True
                            created_responses.append(response_data)
                            console.print(f"[green]✓ Submitted response to {survey['name']}[/green]")
                            submitted = True
                            break
                            
                    except Exception:
                        continue
                
                if not submitted:
                    console.print(f"[yellow]⚠ Could not submit response to {survey['name']}[/yellow]")
                    response_data["api_success"] = False
                    response_data["submitted"] = False
                    created_responses.append(response_data)
                    
            except Exception as e:
                console.print(f"[red]Error submitting response: {e}[/red]")
                logger.exception("Response submission error")
        
        return created_responses