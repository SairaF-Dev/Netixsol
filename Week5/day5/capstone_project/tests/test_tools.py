# from app.tools import check_github_commits


# result = check_github_commits.invoke({
#     "repository": "octocat/Hello-World"
# })

# print(result)

from app.tools import check_github_commits

result = check_github_commits.invoke({
    "repository": "SairaF-Dev/sre-agent-capstone"
})

print(result)


from app.tools import fetch_server_logs


print("=== User Auth ===")

result = fetch_server_logs.invoke({
    "service_name": "User_Auth_API"
})

print(result)


print("\n=== Unknown Service ===")

result = fetch_server_logs.invoke({
    "service_name": "Payment_Gateway"
})

print(result)


print("\n=== Empty Service ===")

result = fetch_server_logs.invoke({
    "service_name": ""
})

print(result)