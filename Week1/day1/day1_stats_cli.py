def statistic_calculator(numbers):
    if not numbers:
        print("Empty List.")
        return

    # Sort the list for median 
    numbers.sort()
    n = len(numbers)

    # Mean
    mean = sum(numbers) / n
    print(f"Mean: {mean}")

    # Median
    if n % 2 == 0:
        median = (numbers[n // 2 - 1] + numbers[n // 2]) / 2
    else:
        median = numbers[n // 2]
    print(f"Median: {median}")

    # Mode
    counts = {}
    for num in numbers:
        if num in counts:
            counts[num] += 1
        else:
            counts[num] = 1
    
    mode = None
    max_count = 0
    for num in counts:
        if counts[num] > max_count:
            max_count = counts[num]
            mode = num
    
    # Check if there is no unique mode
    if max_count <= 1:
        print("Mode: No unique mode")
    else:
        print(f"Mode: {mode}")

    #  Max and Min
    maximum = numbers[0]
    minimum = numbers[0]
    for num in numbers:
        if num > maximum:
            maximum = num
        if num < minimum:
            minimum = num
            
    print(f"Maximum: {maximum}")
    print(f"Minimum: {minimum}")

# Taking input from the user
user_input = input("Enter numbers separated by spaces: ")
try:
    list_numbers = [int(x) for x in user_input.split()]
    statistic_calculator(list_numbers)
except ValueError:
    print("Invalid input. Please enter valid integers separated by spaces.")
