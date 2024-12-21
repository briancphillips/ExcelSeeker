import xlwt


def create_test_excel():
    workbook = xlwt.Workbook()

    # Sheet 1: Employee Data
    sheet1 = workbook.add_sheet("Employees")

    # Headers
    headers = ["ID", "Name", "Department", "Position", "Email"]
    for col, header in enumerate(headers):
        sheet1.write(0, col, header)

    # Sample data
    employees = [
        [
            1001,
            "John Smith",
            "Engineering",
            "Senior Developer",
            "john.smith@example.com",
        ],
        [
            1002,
            "Sarah Johnson",
            "Marketing",
            "Marketing Manager",
            "sarah.j@example.com",
        ],
        [1003, "Mike Brown", "Engineering", "Developer", "mike.b@example.com"],
        [1004, "Lisa Davis", "HR", "HR Specialist", "lisa.d@example.com"],
        [1005, "James Wilson", "Marketing", "Content Writer", "james.w@example.com"],
    ]

    for row, employee in enumerate(employees, 1):
        for col, value in enumerate(employee):
            sheet1.write(row, col, value)

    # Sheet 2: Project Data
    sheet2 = workbook.add_sheet("Projects")

    # Headers
    project_headers = ["Project ID", "Project Name", "Status", "Lead", "Deadline"]
    for col, header in enumerate(project_headers):
        sheet2.write(0, col, header)

    # Sample project data
    projects = [
        ["P101", "Website Redesign", "In Progress", "John Smith", "2024-03-15"],
        ["P102", "Mobile App Development", "Planning", "Mike Brown", "2024-06-30"],
        ["P103", "Marketing Campaign", "Completed", "Sarah Johnson", "2023-12-31"],
        ["P104", "Employee Portal", "On Hold", "Lisa Davis", "2024-04-01"],
        ["P105", "Content Strategy", "In Progress", "James Wilson", "2024-02-28"],
    ]

    for row, project in enumerate(projects, 1):
        for col, value in enumerate(project):
            sheet2.write(row, col, value)

    # Save the workbook
    workbook.save("sample_data.xls")


if __name__ == "__main__":
    create_test_excel()
    print("Test Excel file 'sample_data.xls' has been created successfully!")
