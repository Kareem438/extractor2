"""Update .env file to use localhost instead of WSL IP"""

env_file_path = r"H:\12-extractor\03-code\.env"

# Read current content
with open(env_file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace WSL IP with localhost
old_url = "DATABASE_URL=postgresql://postgres:postgres@172.24.134.250:5432/knowledge_extraction"
new_url = "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/knowledge_extraction"

if old_url in content:
    content = content.replace(old_url, new_url)
    print("Updated DATABASE_URL to use localhost")
else:
    print("DATABASE_URL already uses localhost or has different format")
    print("Current DATABASE_URL line:")
    for line in content.split('\n'):
        if 'DATABASE_URL' in line:
            print(f"  {line}")

# Write updated content
with open(env_file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n.env file updated successfully")
