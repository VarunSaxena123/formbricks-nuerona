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
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Get environment ID - either from .env or hardcoded
        self.environment_id = self._get_environment_id()
        
        if not self.environment_id:
            console.print("[red]✗ Environment ID not found[/red]")
            console.print("[yellow]Please add FORMBRICKS_ENVIRONMENT_ID to your .env file[/yellow]")
    
    def _get_environment_id(self) -> Optional[str]:
        """Get environment ID - from env variable or hardcoded"""
        # First try from .env
        env_id = os.getenv("FORMBRICKS_ENVIRONMENT_ID")
        
        if env_id:
            console.print(f"[dim]Using environment ID from .env: {env_id[:20]}...[/dim]")
            return env_id
        
        # Hardcoded fallback (from your database query)
        hardcoded_id = "cmjmioo9e0004l801j2yksppg"
        console.print(f"[yellow]⚠ Using hardcoded environment ID: {hardcoded_id[:20]}...[/yellow]")
        return hardcoded_id
    
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
                    headers=self.headers,
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
        """Create surveys via Formbricks API with CORRECT multipleChoice format"""
        created_surveys = []
        
        if not self.environment_id:
            console.print("[red]✗ Cannot create surveys without environment ID[/red]")
            return self._create_mock_surveys(surveys_data)
        
        console.print(f"[dim]Using environment ID: {self.environment_id[:20]}...[/dim]")
        
        for i, survey_data in enumerate(surveys_data, 1):
            try:
                # Store the generated survey ID for mapping
                generated_survey_id = f"survey_{i}"
                
                # Convert questions to Formbricks API format
                questions = []
                for q_idx, q in enumerate(survey_data.get("questions", []), 1):
                    question = {
                        "id": q.get("id", f"question{q_idx}"),
                        "type": q.get("type", "openText"),
                        "headline": {"default": q.get("headline", f"Question {q_idx}")},
                        "required": q.get("required", False),
                        "isDraft": False,
                        "logic": []
                    }
                    
                    # Add type-specific fields
                    q_type = q.get("type")
                    
                    if q_type == "rating":
                        question.update({
                            "scale": "number",
                            "range": q.get("range", 5),
                            "labels": {
                                "left": {"default": q.get("labels", {}).get("left", "Poor")},
                                "right": {"default": q.get("labels", {}).get("right", "Excellent")},
                                "center": {"default": ""}
                            }
                        })
                    
                    elif q_type == "multipleChoice":
                        # CORRECT FORMAT: Change type to multipleChoiceMulti and format choices properly
                        question["type"] = "multipleChoiceMulti"
                        
                        # Format choices as array of objects with id and label
                        choices = q.get("choices", ["Option 1", "Option 2"])
                        formatted_choices = []
                        
                        for choice_idx, choice in enumerate(choices):
                            formatted_choices.append({
                                "id": f"choice_{choice_idx+1}",
                                "label": {"default": str(choice)}
                            })
                        
                        question.update({
                            "choices": formatted_choices,
                            "multiSelect": False,  # Set to True for multi-select
                            "shuffleOption": "none"
                        })
                    
                    elif q_type == "openText":
                        question.update({
                            "placeholder": {"default": q.get("placeholder", "")},
                            "longAnswer": False,
                            "inputType": "text"
                        })
                    
                    questions.append(question)
                
                # Build the payload
                payload = {
                    "environmentId": self.environment_id,
                    "name": survey_data["name"],
                    "type": "link",
                    "questions": questions,
                    "welcomeCard": {
                        "enabled": False,
                        "headline": {"default": ""},
                        "html": {"default": ""},
                        "timeToFinish": False,
                        "showResponseCount": False
                    },
                    "thankYouCard": {
                        "enabled": True,
                        "headline": {"default": "Thank you!"},
                        "html": {"default": "Your response has been recorded."},
                        "showResponseCount": False
                    },
                    "displayOption": "displayOnce",
                    "recontactDays": 0,
                    "status": "inProgress"
                }
                
                # Make the API call
                response = requests.post(
                    f"{self.base_url}/api/v1/management/surveys",
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    actual_survey_id = result.get("data", {}).get("id", f"survey_{len(created_surveys)}")
                    
                    survey_info = {
                        "id": actual_survey_id,
                        "name": survey_data["name"],
                        "questions": questions,
                        "api_success": True,
                        "response_data": result,
                        "survey_id": actual_survey_id,
                        "generated_id": generated_survey_id,  # Store the generated ID for mapping
                        "position": i  # Store position for mapping
                    }
                    created_surveys.append(survey_info)
                    console.print(f"[green]✓ Created survey: {survey_data['name']}[/green]")
                    console.print(f"[dim]  Generated ID: {generated_survey_id} → API ID: {actual_survey_id}[/dim]")
                    
                    # Log if we converted multipleChoice
                    if any(q.get("type") == "multipleChoiceMulti" for q in questions):
                        console.print(f"[dim]  Note: Contains multipleChoice questions[/dim]")
                        
                else:
                    error_msg = response.text[:200]
                    console.print(f"[yellow]⚠ Survey creation failed: {response.status_code}[/yellow]")
                    console.print(f"[dim]  Error: {error_msg}[/dim]")
                    
                    # Create mock record with generated ID
                    created_surveys.append({
                        "id": f"mock_survey_{len(created_surveys)}",
                        "name": survey_data["name"],
                        "api_success": False,
                        "error": f"HTTP {response.status_code}",
                        "generated_id": generated_survey_id,
                        "position": i
                    })
                    
            except Exception as e:
                console.print(f"[red]Error creating survey '{survey_data.get('name')}': {e}[/red]")
                created_surveys.append({
                    "id": f"error_survey_{len(created_surveys)}",
                    "name": survey_data.get("name", "Unknown"),
                    "api_success": False,
                    "error": str(e),
                    "generated_id": f"survey_{i}",
                    "position": i
                })
        
        # Print mapping summary
        successful_surveys = [s for s in created_surveys if s.get("api_success")]
        console.print(f"\n[bold]Survey Creation Summary:[/bold]")
        console.print(f"[green]✓ Successfully created {len(successful_surveys)}/{len(surveys_data)} surveys[/green]")
        
        if successful_surveys:
            console.print(f"\n[dim]Survey ID Mapping (for response submission):[/dim]")
            for survey in successful_surveys:
                console.print(f"[dim]  {survey.get('generated_id', 'N/A')} → {survey.get('id')} ({survey['name']})[/dim]")
        
        return created_surveys
    
    def _create_mock_surveys(self, surveys_data: List[Dict]) -> List[Dict]:
        """Create mock survey records when API fails"""
        return [
            {
                "id": f"mock_survey_{i}",
                "name": survey["name"],
                "api_success": False,
                "note": "Mock survey - API failed",
                "generated_id": f"survey_{i+1}",
                "position": i+1
            }
            for i, survey in enumerate(surveys_data)
        ]
    
    def submit_responses(self, responses_data: List[Dict], created_surveys: List[Dict]) -> List[Dict]:
        """Submit responses via Formbricks Client API with proper ID mapping"""
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
        
        console.print(f"[dim]Found {len(api_surveys)} API-created surveys for response submission[/dim]")
        
        # Create mapping from generated survey IDs to actual API survey IDs
        # We'll use position-based mapping since generated data uses survey_1, survey_2, etc.
        survey_mapping = {}
        for survey in api_surveys:
            generated_id = survey.get("generated_id")
            position = survey.get("position")
            
            if generated_id:
                survey_mapping[generated_id] = survey
            elif position:
                # Create mapping based on position
                survey_mapping[f"survey_{position}"] = survey
        
        console.print(f"[dim]Created mapping for {len(survey_mapping)} surveys[/dim]")
        
        response_count = 0
        skipped_count = 0
        
        for response_data in responses_data:
            try:
                generated_survey_id = response_data.get("survey_id")  # e.g., "survey_1"
                
                if not generated_survey_id:
                    console.print(f"[dim]Response has no survey_id, skipping[/dim]")
                    skipped_count += 1
                    response_data["api_success"] = False
                    response_data["submitted"] = False
                    created_responses.append(response_data)
                    continue
                
                # Find the corresponding API survey
                api_survey = survey_mapping.get(generated_survey_id)
                
                if not api_survey:
                    # Try to extract survey number and map by position
                    if generated_survey_id.startswith("survey_"):
                        try:
                            survey_num = int(generated_survey_id.split("_")[1])
                            # Find survey by position
                            for survey in api_surveys:
                                if survey.get("position") == survey_num:
                                    api_survey = survey
                                    break
                        except:
                            pass
                
                if not api_survey:
                    console.print(f"[dim]Could not map {generated_survey_id} to API survey, skipping[/dim]")
                    skipped_count += 1
                    response_data["api_success"] = False
                    response_data["submitted"] = False
                    created_responses.append(response_data)
                    continue
                
                actual_survey_id = api_survey.get("survey_id") or api_survey.get("id")
                survey_name = api_survey.get("name", "Unknown")
                
                if not actual_survey_id:
                    console.print(f"[yellow]⚠ No ID found for API survey: {survey_name}[/yellow]")
                    skipped_count += 1
                    response_data["api_success"] = False
                    response_data["submitted"] = False
                    created_responses.append(response_data)
                    continue
                
                # Prepare response payload
                response_payload = {
                    "surveyId": actual_survey_id,
                    "responses": response_data.get("data", {}),
                    "finished": True,
                    "ttc": response_data.get("ttc", 30),
                    "userId": response_data.get("user_id", str(uuid.uuid4()))
                }
                
                # Try to submit response
                submitted = False
                
                # Try different endpoints
                endpoints = [
                    f"{self.base_url}/api/v1/client/responses",
                    f"{self.base_url}/api/v1/responses",
                ]
                
                for endpoint in endpoints:
                    try:
                        response = requests.post(
                            endpoint,
                            json=response_payload,
                            timeout=30,
                            headers={"Content-Type": "application/json"}
                        )
                        
                        if response.status_code in [200, 201]:
                            response_data["api_success"] = True
                            response_data["submitted"] = True
                            response_data["api_survey_id"] = actual_survey_id
                            response_data["endpoint_used"] = endpoint
                            response_data["mapped_from"] = generated_survey_id
                            created_responses.append(response_data)
                            
                            response_count += 1
                            console.print(f"[green]✓ Submitted response to {survey_name} (from {generated_survey_id})[/green]")
                            submitted = True
                            break
                        else:
                            # Try with different format
                            alternative_payload = {
                                "data": response_data.get("data", {}),
                                "surveyId": actual_survey_id,
                                "userId": response_data.get("user_id", str(uuid.uuid4()))
                            }
                            
                            alt_response = requests.post(
                                endpoint,
                                json=alternative_payload,
                                timeout=30,
                                headers={"Content-Type": "application/json"}
                            )
                            
                            if alt_response.status_code in [200, 201]:
                                response_data["api_success"] = True
                                response_data["submitted"] = True
                                response_data["api_survey_id"] = actual_survey_id
                                response_data["endpoint_used"] = endpoint + " (alt format)"
                                response_data["mapped_from"] = generated_survey_id
                                created_responses.append(response_data)
                                
                                response_count += 1
                                console.print(f"[green]✓ Submitted response (alt format) to {survey_name}[/green]")
                                submitted = True
                                break
                            
                    except Exception as e:
                        console.print(f"[dim]Endpoint {endpoint} error: {e}[/dim]")
                        continue
                
                if not submitted:
                    console.print(f"[yellow]⚠ Could not submit response to {survey_name}[/yellow]")
                    response_data["api_success"] = False
                    response_data["submitted"] = False
                    created_responses.append(response_data)
                    skipped_count += 1
                    
            except Exception as e:
                console.print(f"[red]Error submitting response: {e}[/red]")
                logger.exception("Response submission error")
                skipped_count += 1
        
        console.print(f"\n[bold]Response Submission Summary:[/bold]")
        console.print(f"[green]✓ Successfully submitted: {response_count}[/green]")
        console.print(f"[yellow]⚠ Skipped/Failed: {skipped_count}[/yellow]")
        console.print(f"[dim]Total responses processed: {len(responses_data)}[/dim]")
        
        return created_responses
    
    def _log_api_error(self, operation: str, payload: Dict, response):
        """Log API errors for debugging"""
        error_log = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "operation": operation,
            "status_code": response.status_code,
            "response": response.text,
            "payload_preview": {k: v for k, v in payload.items() if k != "questions"}
        }
        
        # Save to error log file
        os.makedirs("logs", exist_ok=True)
        with open(f"logs/api_errors_{time.strftime('%Y%m%d')}.json", "a") as f:
            f.write(json.dumps(error_log) + "\n")
