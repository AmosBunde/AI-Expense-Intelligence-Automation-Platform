"""
Load testing for the Expense Intelligence Platform using Locust.
Run: locust -f tests/load/locustfile.py --host=http://localhost:8000
"""
import json
import random

from locust import HttpUser, between, task


class ExpenseUser(HttpUser):
    """Simulates typical user behavior on the expense platform."""
    wait_time = between(1, 5)
    token = None

    def on_start(self):
        """Login and get JWT token."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password"},
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def list_expenses(self):
        """Most common action: browse expenses."""
        page = random.randint(1, 5)
        self.client.get(
            f"/api/v1/expenses?page={page}&page_size=20",
            headers=self.headers,
            name="/api/v1/expenses",
        )

    @task(2)
    def view_expense_detail(self):
        """View a single expense."""
        expense_id = f"exp-{random.randint(1, 100)}"
        self.client.get(
            f"/api/v1/expenses/{expense_id}",
            headers=self.headers,
            name="/api/v1/expenses/[id]",
        )

    @task(1)
    def upload_expense(self):
        """Upload a receipt."""
        self.client.post(
            "/api/v1/expenses/upload",
            headers=self.headers,
            files={"file": ("receipt.jpg", b"fake-receipt-data", "image/jpeg")},
            data={"document_type": "receipt"},
            name="/api/v1/expenses/upload",
        )

    @task(2)
    def view_analytics(self):
        """Check spend analytics."""
        period = random.choice(["week", "month", "quarter"])
        self.client.get(
            f"/api/v1/analytics/spend-summary?period={period}",
            headers=self.headers,
            name="/api/v1/analytics/spend-summary",
        )

    @task(1)
    def chat_with_ai(self):
        """Ask the AI assistant a question."""
        questions = [
            "What is my total spend this month?",
            "Which category has the highest spend?",
            "Are there any flagged expenses?",
            "Show me my travel expenses",
        ]
        self.client.post(
            "/api/v1/ai/chat",
            headers=self.headers,
            json={"message": random.choice(questions)},
            name="/api/v1/ai/chat",
        )

    @task(1)
    def check_health(self):
        """Health check endpoint."""
        self.client.get("/health", name="/health")


class FinanceAdmin(HttpUser):
    """Simulates finance team admin behavior."""
    wait_time = between(3, 10)
    weight = 1  # Lower weight: fewer admin users
    token = None

    def on_start(self):
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "password"},
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def view_analytics(self):
        self.client.get(
            "/api/v1/analytics/spend-summary?period=month",
            headers=self.headers,
            name="/api/v1/analytics/spend-summary [admin]",
        )

    @task(2)
    def view_anomalies(self):
        self.client.get(
            "/api/v1/analytics/anomalies",
            headers=self.headers,
            name="/api/v1/analytics/anomalies",
        )

    @task(1)
    def list_policies(self):
        self.client.get(
            "/api/v1/policies",
            headers=self.headers,
            name="/api/v1/policies",
        )
