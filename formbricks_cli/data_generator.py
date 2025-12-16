import json
import os
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from rich.console import Console
import logging

console = Console()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataGenerator:
    """Generates realistic data for Formbricks"""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.use_openai = bool(self.openai_api_key)
        
        if self.use_openai:
            try:
                # Try to import OpenAI - handle different versions
                import openai
                from importlib.metadata import version
                
                # Check OpenAI version
                openai_version = version("openai")
                logger.info(f"Using OpenAI version: {openai_version}")
                
                if openai_version.startswith("0."):
                    # Old version (<1.0.0)
                    openai.api_key = self.openai_api_key
                    self.client = openai
                    self.use_old_version = True
                else:
                    # New version (>=1.0.0)
                    from openai import OpenAI
                    self.client = OpenAI(api_key=self.openai_api_key)
                    self.use_old_version = False
                    
            except ImportError:
                console.print("[yellow]OpenAI package not installed. Using mock data generation.[/yellow]")
                self.use_openai = False
                self.use_old_version = False
            except Exception as e:
                console.print(f"[yellow]Failed to initialize OpenAI: {e}. Using mock data.[/yellow]")
                self.use_openai = False
                self.use_old_version = False
        else:
            console.print("[yellow]No OpenAI API key found. Using mock data generation.[/yellow]")
            self.use_openai = False
            self.use_old_version = False
    
    def generate_surveys(self, count: int = 5) -> List[Dict]:
        """Generate realistic surveys"""
        surveys = []
        
        survey_types = [
            ("Customer Satisfaction Survey", "customer feedback about services"),
            ("Employee Engagement Survey", "employee satisfaction and workplace feedback"),
            ("Product Feedback Survey", "user feedback about a software product"),
            ("Market Research Survey", "consumer preferences and market trends"),
            ("Website Usability Survey", "user experience on a website")
        ]
        
        # Ensure we have exactly 5 surveys as required
        count = min(count, len(survey_types))
        
        for i in range(count):
            survey_name, survey_context = survey_types[i]
            
            if self.use_openai:
                survey = self._generate_survey_with_llm(survey_name, survey_context)
            else:
                survey = self._generate_mock_survey(survey_name, survey_context)
            
            # Ensure required fields
            survey["id"] = f"survey_{i+1}"
            survey["created_at"] = (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
            survey["updated_at"] = datetime.now().isoformat()
            survey["status"] = "inProgress"
            
            surveys.append(survey)
        
        return surveys
    
    def generate_users(self, count: int = 10) -> List[Dict]:
        """Generate realistic users with Manager or Owner roles"""
        first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Quinn", "Avery", "Skyler", "Dakota"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        companies = ["TechCorp", "InnovateInc", "DigitalSolutions", "FutureLabs", "CloudSystems"]
        domains = ["com", "io", "co", "ai", "dev"]
        
        users = []
        for i in range(count):
            first = random.choice(first_names)
            last = random.choice(last_names)
            company = random.choice(companies)
            domain = random.choice(domains)
            
            user = {
                "id": f"user_{i+1}",
                "name": f"{first} {last}",
                "email": f"{first.lower()}.{last.lower()}@{company.lower()}.{domain}",
                "role": "owner" if i < 2 else "manager",  # First 2 are owners, rest are managers
                "company": company,
                "created_at": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
                "last_login": (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat()
            }
            users.append(user)
        
        return users
    
    def generate_responses(self, surveys: List[Dict], users: List[Dict]) -> List[Dict]:
        """Generate realistic responses for surveys"""
        responses = []
        response_id = 1
        
        # Ensure at least 1 response per survey
        for survey in surveys:
            # For each survey, generate responses from different users
            available_users = users.copy()
            random.shuffle(available_users)
            
            # Generate responses (at least 1, up to min(3, len(available_users)))
            num_responses = random.randint(1, min(3, len(available_users)))
            
            for i in range(num_responses):
                if i >= len(available_users):
                    break
                    
                user = available_users[i]
                
                if self.use_openai:
                    response_data = self._generate_response_with_llm(survey, user)
                else:
                    response_data = self._generate_mock_response(survey, user)
                
                response = {
                    "id": f"response_{response_id}",
                    "survey_id": survey["id"],
                    "user_id": user["id"],
                    "created_at": (datetime.now() - timedelta(hours=random.randint(1, 168))).isoformat(),
                    "data": response_data,
                    "ttc": random.randint(30, 300)  # Time to complete in seconds
                }
                
                responses.append(response)
                response_id += 1
        
        return responses
    
    def _generate_survey_with_llm(self, name: str, context: str) -> Dict:
        """Generate survey using OpenAI with version compatibility"""
        try:
            prompt = f"""Generate a realistic survey about {context} with the name "{name}".
            
            Return ONLY valid JSON in this exact format:
            {{
                "name": "Survey Name",
                "type": "link",
                "questions": [
                    {{
                        "type": "rating",
                        "id": "q1",
                        "headline": "Question text here",
                        "required": true,
                        "range": 5,
                        "labels": {{
                            "left": "Very Poor",
                            "right": "Excellent"
                        }}
                    }}
                ],
                "thankYouCard": {{
                    "enabled": true,
                    "headline": "Thank you message",
                    "subheader": "Additional thank you text"
                }}
            }}
            
            Requirements:
            - The survey must have 3-5 questions
            - Mix different question types (rating, multipleChoice, openText)
            - Ensure all questions have unique IDs like "q1", "q2", etc.
            - Make questions realistic and relevant to the survey topic"""
            
            if self.use_old_version:
                # OpenAI < 1.0.0
                response = self.client.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a survey design expert. Always respond with valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                content = response.choices[0].message.content
            else:
                # OpenAI >= 1.0.0
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a survey design expert. Always respond with valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                content = response.choices[0].message.content
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                survey_data = json.loads(json_match.group())
                # Ensure all questions have IDs
                for i, question in enumerate(survey_data.get("questions", []), 1):
                    if "id" not in question:
                        question["id"] = f"q{i}"
                return survey_data
                
        except Exception as e:
            console.print(f"[yellow]LLM survey generation failed: {e}, using mock data[/yellow]")
            logger.exception("LLM survey generation error")
        
        return self._generate_mock_survey(name, context)
    
    def _generate_mock_survey(self, name: str, context: str) -> Dict:
        """Generate mock survey data"""
        question_templates = {
            "rating": [
                {"type": "rating", "headline": "How satisfied are you with our service?", "required": True, "range": 5, "labels": {"left": "Very Dissatisfied", "right": "Very Satisfied"}},
                {"type": "rating", "headline": "How likely are you to recommend us to others?", "required": True, "range": 10, "labels": {"left": "Not at all likely", "right": "Extremely likely"}},
                {"type": "rating", "headline": "Rate the quality of our product", "required": True, "range": 7, "labels": {"left": "Poor", "right": "Excellent"}}
            ],
            "multipleChoice": [
                {"type": "multipleChoice", "headline": "Which features do you use most often?", "required": False, "choices": ["Feature A", "Feature B", "Feature C", "Feature D"]},
                {"type": "multipleChoice", "headline": "How did you hear about us?", "required": False, "choices": ["Social Media", "Search Engine", "Friend/Colleague", "Advertisement", "Other"]},
                {"type": "multipleChoice", "headline": "What is your primary role?", "required": True, "choices": ["Individual Contributor", "Manager", "Director", "Executive"]}
            ],
            "openText": [
                {"type": "openText", "headline": "What do you like most about our service?", "required": False, "placeholder": "Your thoughts..."},
                {"type": "openText", "headline": "What can we improve?", "required": False, "placeholder": "Your suggestions..."},
                {"type": "openText", "headline": "Additional comments or feedback?", "required": False, "placeholder": "Any other feedback..."}
            ]
        }
        
        # Select 3-5 random questions
        num_questions = random.randint(3, 5)
        questions = []
        
        # Ensure variety of question types
        question_types = ["rating", "multipleChoice", "openText"]
        weights = [0.4, 0.3, 0.3]  # Prefer ratings, but include others
        
        for i in range(num_questions):
            q_type = random.choices(question_types, weights=weights, k=1)[0]
            question = random.choice(question_templates[q_type]).copy()
            question["id"] = f"q{i+1}"
            questions.append(question)
        
        thank_you_messages = [
            {"headline": "Thank You!", "subheader": "Your feedback helps us improve."},
            {"headline": "Survey Complete", "subheader": "We appreciate you taking the time."},
            {"headline": "Thanks for your feedback!", "subheader": "Your responses are valuable to us."}
        ]
        
        thank_you = random.choice(thank_you_messages)
        
        return {
            "name": name,
            "type": "link",
            "questions": questions,
            "thankYouCard": {
                "enabled": True,
                "headline": thank_you["headline"],
                "subheader": thank_you["subheader"]
            }
        }
    
    def _generate_response_with_llm(self, survey: Dict, user: Dict) -> Dict:
        """Generate realistic response using OpenAI with version compatibility"""
        try:
            # Format questions for prompt
            questions_text = []
            for i, q in enumerate(survey.get("questions", []), 1):
                q_id = q.get("id", f"q{i}")
                q_type = q.get("type", "text")
                q_headline = q.get("headline", f"Question {i}")
                questions_text.append(f"- ID: {q_id} | Type: {q_type} | Question: {q_headline}")
            
            questions_list = "\n".join(questions_text)
            
            prompt = f"""Generate realistic survey responses for the following questions from a user named {user['name']} ({user['email']}) who works at {user['company']}:
            
            {questions_list}
            
            Return ONLY a JSON object where:
            - Keys are question IDs (e.g., "q1", "q2")
            - Values are appropriate responses based on question types:
              * For rating questions: a number between 1 and the max range
              * For multipleChoice: one of the provided choices
              * For openText: a realistic, thoughtful response
            
            Example format:
            {{
                "q1": "4",
                "q2": "Feature A",
                "q3": "The interface is very user-friendly and intuitive."
            }}"""
            
            if self.use_old_version:
                response = self.client.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a survey respondent. Generate realistic, varied responses that match the user profile."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                    max_tokens=500
                )
                content = response.choices[0].message.content
            else:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a survey respondent. Generate realistic, varied responses that match the user profile."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                    max_tokens=500
                )
                content = response.choices[0].message.content
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
                
        except Exception as e:
            console.print(f"[yellow]LLM response generation failed: {e}[/yellow]")
            logger.exception("LLM response generation error")
        
        return self._generate_mock_response(survey, user)
    
    def _generate_mock_response(self, survey: Dict, user: Dict) -> Dict:
        """Generate mock response data"""
        response_data = {}
        
        for i, question in enumerate(survey.get("questions", []), 1):
            q_id = question.get("id", f"q{i}")
            q_type = question.get("type", "openText")
            
            if q_type == "rating":
                max_range = question.get("range", 5)
                # Generate slightly optimistic ratings (skewed toward 3-5 on 5-point scale)
                if max_range == 5:
                    rating = random.choices([1, 2, 3, 4, 5], weights=[0.05, 0.1, 0.2, 0.3, 0.35])[0]
                else:
                    rating = random.randint(1, max_range)
                response_data[q_id] = str(rating)
                
            elif q_type == "multipleChoice":
                choices = question.get("choices", ["Option A", "Option B"])
                response_data[q_id] = random.choice(choices)
                
            else:  # openText
                responses = [
                    "Great service, very satisfied with the overall experience.",
                    "Could use some improvement in response time, but generally good.",
                    "Excellent product, easy to use and intuitive interface.",
                    "The interface could be more intuitive, but functionality is solid.",
                    "Very helpful customer support team, very responsive.",
                    "Some features are missing that would be really useful.",
                    "Overall good experience, would recommend to colleagues.",
                    "The product meets our needs effectively, good value for money.",
                    "There's a learning curve but once you get used to it, it's powerful.",
                    "Reliable service with good uptime and performance."
                ]
                response_data[q_id] = random.choice(responses)
        
        return response_data