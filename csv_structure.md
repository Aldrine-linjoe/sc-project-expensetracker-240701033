# CSV File Structure

The project uses CSV files for storage. Both files are created automatically in the `data` folder when the app runs.

## data/users.csv

```csv
id,username,email,password_hash,salt,created_at
```

| Column | Description |
| --- | --- |
| id | Unique user id |
| username | Name entered during registration |
| email | Unique login email |
| password_hash | Secure salted password hash |
| salt | Salt used while hashing the password |
| created_at | Registration date and time |

## data/expenses.csv

```csv
id,user_id,amount,category,description,expense_date,created_at
```

| Column | Description |
| --- | --- |
| id | Unique expense id |
| user_id | User id linked with `users.csv` |
| amount | Expense amount |
| category | Expense category |
| description | Expense details |
| expense_date | Date selected by the user |
| created_at | Date and time when expense was saved |
