class SchoolYear:
    def __init__(self):
        self.current_day_count = 0
        self.completed_subjects = []

    def check_days_remaining(self):
        if self.current_day_count < 180:
            days_remaining = 180 - self.current_day_count
            print(f"Days remaining: {days_remaining}")
        else:
            print("You have completed the 180 required days!")

    def log_days(self, days):
        self.current_day_count += days

# Test simulation
if __name__ == "__main__":
    # Create an instance of SchoolYear
    school = SchoolYear()
    
    # Simulate logging 5 days
    print("Logging 5 days of school...")
    school.log_days(5)
    
    # Check and print the result
    school.check_days_remaining()
