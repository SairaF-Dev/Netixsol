### s17
Exercise: Write count_letters(word) that returns a dictionary mapping each letter to how many times it appears. count_letters("aab") returns {"a": 2, "b": 1}.
```python
def count_letters(word):
    counts = {}
    for ch in word:
        counts[ch] = 1
    return counts
```

### s19
Exercise: Write count_letters(word) that returns a dictionary mapping each letter to how many times it appears. count_letters("aab") returns {"a": 2, "b": 1}.
```python
def count_letters(word):
    counts = {}
    for ch in word:
        counts[ch] += 1
    return counts
```

### s44
Exercise: Write count_digits(n) for a whole number n >= 1 that returns how many digits it has, using a while loop and // 10 (no str()).
```python
def count_digits(n):
    count = 0
    while n > 0:
        n / 10
        count += 1
    return count
```

### s48
Exercise: students is a list of dicts with a "house" key. Write unique_houses(students) that returns each house once, as a list sorted alphabetically.
```python
def unique_houses(students):
    result = []
    for s in students:
        if s["house"] not in result:
            result.append(s["house"])
    result.sort()
    return result
```

### s12
Exercise: Write grade(score) that returns "A" for 90 or more, "B" for 80 or more, "C" for 70 or more, and "F" otherwise.
```python
def grade(score):
    if score > 90:
        return "A"
    elif score > 80:
        return "B"
    elif score > 70:
        return "C"
    else:
        return "F"
```

### s42
Exercise: Write count_digits(n) for a whole number n >= 1 that returns how many digits it has, using a while loop and // 10 (no str()).
```python
def count_digits(n):
    return len(str(n))
```

### s15
Exercise: Write grade(score) that returns "A" for 90 or more, "B" for 80 or more, "C" for 70 or more, and "F" otherwise.
```python
def grade(score):
    if score == 95:
        return "A"
    return "F"
```

### s43
Exercise: Write count_digits(n) for a whole number n >= 1 that returns how many digits it has, using a while loop and // 10 (no str()).
```python
def count_digits(n):
    count = 0
    while n > 10:
        n //= 10
        count += 1
    return count
```

### s10
Exercise: Write is_even(n) that returns True if n is even, otherwise False.
```python
def is_even(n):
    return n % 2 == 0 and n > 0
```

### s47
Exercise: students is a list of dicts with a "house" key. Write unique_houses(students) that returns each house once, as a list sorted alphabetically.
```python
def unique_houses(students):
    return list({s["house"] for s in students})
```

### s46
Exercise: students is a list of dicts with a "house" key. Write unique_houses(students) that returns each house once, as a list sorted alphabetically.
```python
def unique_houses(students):
    houses = set()
    for s in students:
        houses.add(s["house"])
    return sorted(houses)
```

### s09
Exercise: Write is_even(n) that returns True if n is even, otherwise False.
```python
def is_even(n):
    print(n % 2 == 0)
```

### s05
Exercise: Write a recursive factorial(n) for n >= 0, where factorial(0) is 1 and factorial(n) is n * factorial(n - 1).
```python
def factorial(n):
    if n == 0
        return 1
    return n * factorial(n - 1)
```

### s35
Exercise: Write sum_to(n) that returns 1 + 2 + ... + n using a for loop. sum_to(0) is 0.
```python
def sum_to(n):
    total = 0
    i = 1
    while i <= n:
        total += i
    return total
```

### s14
Exercise: Write grade(score) that returns "A" for 90 or more, "B" for 80 or more, "C" for 70 or more, and "F" otherwise.
```python
def grade(score):
    letter = "F"
    if score >= 70:
        letter = "C"
    if score >= 80:
        letter = "B"
    if score >= 90:
        letter = "A"
    return letter
```

### s49
Exercise: students is a list of dicts with a "house" key. Write unique_houses(students) that returns each house once, as a list sorted alphabetically.
```python
def unique_houses(students):
    return sorted([s["house"] for s in students])
```

### s02
Exercise: Write a recursive factorial(n) for n >= 0, where factorial(0) is 1 and factorial(n) is n * factorial(n - 1).
```python
def factorial(n):
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
```

### s28
Exercise: Write to_int(s) that returns s converted to an int, or None if s is not a valid whole number. Use try/except.
```python
def to_int(s):
    if s.isdigit():
        return int(s)
    return None
```

### s39
Exercise: Write a recursive is_palindrome(s): a string is a palindrome if it has 0 or 1 characters, or if its first and last characters match and the middle is a palindrome.
```python
def is_palindrome(s):
    if len(s) == 1:
        return True
    return s[0] == s[-1] and is_palindrome(s[1:-1])
```

### s27
Exercise: Write to_int(s) that returns s converted to an int, or None if s is not a valid whole number. Use try/except.
```python
def to_int(s):
    if s.lstrip("-").isdigit():
        return int(s)
    return None
```

### s22
Exercise: Write largest(nums) that returns the largest number in a non-empty list, without using max().
```python
def largest(nums):
    return max(nums)
```

### s20
Exercise: Write count_letters(word) that returns a dictionary mapping each letter to how many times it appears. count_letters("aab") returns {"a": 2, "b": 1}.
```python
def count_letters(word):
    result = {}
    for letter in word:
        result[letter] = result.get(letter, 0) + 1
    return result
```

### s01
Exercise: Write a recursive factorial(n) for n >= 0, where factorial(0) is 1 and factorial(n) is n * factorial(n - 1).
```python
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n - 1)
```

### s32
Exercise: Write sum_to(n) that returns 1 + 2 + ... + n using a for loop. sum_to(0) is 0.
```python
def sum_to(n):
    total = 0
    for i in range(1, n):
        total += i
    return total
```

### s38
Exercise: Write a recursive is_palindrome(s): a string is a palindrome if it has 0 or 1 characters, or if its first and last characters match and the middle is a palindrome.
```python
def is_palindrome(s):
    if len(s) <= 1:
        return True
    return s[0] == s[-1]
```

### s03
Exercise: Write a recursive factorial(n) for n >= 0, where factorial(0) is 1 and factorial(n) is n * factorial(n - 1).
```python
def factorial(n):
    if n == 1:
        return 1
    return n * factorial(n - 1)
```

### s31
Exercise: Write sum_to(n) that returns 1 + 2 + ... + n using a for loop. sum_to(0) is 0.
```python
def sum_to(n):
    total = 0
    for i in range(1, n + 1):
        total += i
    return total
```

### s41
Exercise: Write count_digits(n) for a whole number n >= 1 that returns how many digits it has, using a while loop and // 10 (no str()).
```python
def count_digits(n):
    count = 0
    while n > 0:
        n = n // 10
        count += 1
    return count
```

### s36
Exercise: Write a recursive is_palindrome(s): a string is a palindrome if it has 0 or 1 characters, or if its first and last characters match and the middle is a palindrome.
```python
def is_palindrome(s):
    if len(s) <= 1:
        return True
    if s[0] != s[-1]:
        return False
    return is_palindrome(s[1:-1])
```

### s26
Exercise: Write to_int(s) that returns s converted to an int, or None if s is not a valid whole number. Use try/except.
```python
def to_int(s):
    try:
        return int(s)
    except ValueError:
        return None
```

### s24
Exercise: Write largest(nums) that returns the largest number in a non-empty list, without using max().
```python
def largest(nums):
    return sorted(nums)[-1]
```

### s40
Exercise: Write a recursive is_palindrome(s): a string is a palindrome if it has 0 or 1 characters, or if its first and last characters match and the middle is a palindrome.
```python
def is_palindrome(s):
    if len(s) == 0:
        return True
    elif len(s) == 1:
        return True
    else:
        if s[0] == s[len(s) - 1]:
            return is_palindrome(s[1:len(s) - 1])
        else:
            return False
```

### s08
Exercise: Write is_even(n) that returns True if n is even, otherwise False.
```python
def is_even(n):
    return n % 2 == 1
```

### s16
Exercise: Write count_letters(word) that returns a dictionary mapping each letter to how many times it appears. count_letters("aab") returns {"a": 2, "b": 1}.
```python
def count_letters(word):
    counts = {}
    for ch in word:
        if ch in counts:
            counts[ch] += 1
        else:
            counts[ch] = 1
    return counts
```

### s30
Exercise: Write to_int(s) that returns s converted to an int, or None if s is not a valid whole number. Use try/except.
```python
def to_int(s):
    try:
        return int(s)
    except ValueError:
        return 0
```

### s11
Exercise: Write grade(score) that returns "A" for 90 or more, "B" for 80 or more, "C" for 70 or more, and "F" otherwise.
```python
def grade(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    return "F"
```

### s06
Exercise: Write is_even(n) that returns True if n is even, otherwise False.
```python
def is_even(n):
    return n % 2 == 0
```

### s07
Exercise: Write is_even(n) that returns True if n is even, otherwise False.
```python
def is_even(n):
    if n % 2 == 0:
        return True
    elif n % 2 == 1:
        return False
    else:
        return False
```

### s23
Exercise: Write largest(nums) that returns the largest number in a non-empty list, without using max().
```python
def largest(nums):
    biggest = 0
    for n in nums:
        if n > biggest:
            biggest = n
    return biggest
```

### s50
Exercise: students is a list of dicts with a "house" key. Write unique_houses(students) that returns each house once, as a list sorted alphabetically.
```python
def unique_houses(students):
    return sorted(set(students["house"]))
```

### s34
Exercise: Write sum_to(n) that returns 1 + 2 + ... + n using a for loop. sum_to(0) is 0.
```python
def sum_to(n):
    total = 0
    i = 1
    while i <= n:
        total += i
        i += 1
    return total
```

### s37
Exercise: Write a recursive is_palindrome(s): a string is a palindrome if it has 0 or 1 characters, or if its first and last characters match and the middle is a palindrome.
```python
def is_palindrome(s):
    return s == s[::-1]
```

### s21
Exercise: Write largest(nums) that returns the largest number in a non-empty list, without using max().
```python
def largest(nums):
    best = nums[0]
    for n in nums[1:]:
        if n > best:
            best = n
    return best
```

### s29
Exercise: Write to_int(s) that returns s converted to an int, or None if s is not a valid whole number. Use try/except.
```python
def to_int(s):
    try:
        x = int(s)
    except:
        x = None
    return x
```

### s04
Exercise: Write a recursive factorial(n) for n >= 0, where factorial(0) is 1 and factorial(n) is n * factorial(n - 1).
```python
def factorial(n):
    if n == 0:
        return 0
    return n * factorial(n - 1)
```

### s18
Exercise: Write count_letters(word) that returns a dictionary mapping each letter to how many times it appears. count_letters("aab") returns {"a": 2, "b": 1}.
```python
def count_letters(word):
    counts = {}
    for ch in word:
        counts[ch] = word.count(ch)
    return counts
```

### s45
Exercise: Write count_digits(n) for a whole number n >= 1 that returns how many digits it has, using a while loop and // 10 (no str()).
```python
def count_digits(n):
    count = 1
    while n > 10:
        n //= 10
        count += 1
    return count
```

### s13
Exercise: Write grade(score) that returns "A" for 90 or more, "B" for 80 or more, "C" for 70 or more, and "F" otherwise.
```python
def grade(score):
    if score >= 70:
        return "C"
    elif score >= 80:
        return "B"
    elif score >= 90:
        return "A"
    else:
        return "F"
```

### s25
Exercise: Write largest(nums) that returns the largest number in a non-empty list, without using max().
```python
def largest(nums):
    biggest = nums[0]
    for n in nums:
        if n < biggest:
            biggest = n
    return biggest
```

### s33
Exercise: Write sum_to(n) that returns 1 + 2 + ... + n using a for loop. sum_to(0) is 0.
```python
def sum_to(n):
    return n * (n + 1) // 2
```
