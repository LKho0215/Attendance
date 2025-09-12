from core.database import DatabaseManager

db = DatabaseManager()
employees = db.get_all_employees()
print("Current employees in database:")
for emp in employees:
    print(f"- {emp['name']} (ID: {emp['employee_id']})")
