# I keep a variable-size window that contains no duplicates. The right pointer scans each 
# character once. If a character’s prior index is inside the active window, I move the left 
# pointer just past that prior occurrence. I then record the current index and update the 
# best window length. Neither pointer moves backward, so runtime is O(n), with O(k) space 
# for the last-seen map.

# Examples:
# Allow at most 100 requests per customer in the preceding 60 seconds.
# Alert if error rate exceeds 5% over the last five minutes.
# Open a circuit breaker if a dependency has 20 failures in the last 30 seconds.
# Ignore duplicate event IDs seen in the last 24 hours.
# Compare the current value with:
#  the mean and standard deviation of the prior 100 observations.
# Flag an account if it has:
# - 10 failed logins in 5 minutes
# - 5 password-reset attempts in 10 minutes
# - 20 API-key failures in 1 minute
    
def longest_unique_substring_length(text):
    left_pointer = 0
    last_seen = {}
    max_length = 0

    for right_pointer, character in enumerate(text):
        if character in last_seen and last_seen[character] >= left_pointer:
            left_pointer = last_seen[character] + 1

        last_seen[character] = right_pointer
        current_length = right_pointer - left_pointer + 1
        max_length = max(max_length, current_length)

    return max_length


# print(longest_unique_substring_length("abcabcbb"))
# 3
# One answer: "abc"

# print(longest_unique_substring_length("pwwkew"))
# 3
# One answer: "wke"

# print(longest_unique_substring_length(""))
# 0

def merge_intervals(intervals):
    if not intervals:
        return []
    
    intervals.sort()

    merged = [intervals [0]]

# Compare each interval with the most recently merged interval.
    for current_interval in intervals[1:]:
        last_merged_interval = merged[-1]
        current_start = current_interval[0]
        current_end = current_interval[1]

        last_merged_end = last_merged_interval[1]

        if current_start <= last_merged_end:
            last_merged_interval[1] = max(last_merged_end, current_end)
        else:
            merged.append(current_interval)

    return(merged)

intervals = [[1, 3], [2, 6], [8, 10], [15, 18]]

print(merge_intervals(intervals))