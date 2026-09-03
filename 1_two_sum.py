# Two Sum
#
# Goal:
# Return the indices of two distinct numbers whose values add up to target.
#
# Assumptions:
# - nums may be unsorted.
# - nums may contain duplicate values.
# - Return one valid pair of indices; return None if no pair exists.
#
# Approach:
# Scan from left to right while storing previously seen values in a hash map:
#     value -> index
#
# For each value, calculate the complement needed to reach the target:
#     complement = target - value
#
# If that complement was seen earlier, its stored index and the current index
# form a valid answer.
#
# Important invariant:
# `seen` contains only values from indices before the current index.
# We check for the complement BEFORE storing the current value, ensuring that
# the same array element cannot be used twice.
#
# Early termination:
# Return immediately after finding a pair because the contract requires only
# one valid answer. If the requirement changed to return every valid pair,
# we would continue scanning and define duplicate-pair behavior.
#
# Complexity:
# - Time: expected O(n), with one pass through nums and expected O(1) hash lookups.
# - Space: O(n) in the worst case for the `seen` dictionary.


def two_sum(nums: list[int], target: int) -> list[int] | None:
    # Maps each previously seen number to its index.
    seen: dict[int, int] = {}

    for index, value in enumerate(nums):
        # Find the number needed to pair with `value` and reach `target`.
        complement = target - value

        # If the needed value appeared earlier, return the two distinct indices.
        if complement in seen:
            return [seen[complement], index]

        # Store the current value only after checking for its complement.
        seen[value] = index

    # Explicitly define the no-solution behavior.
    return None

nums = [2, 7, 11, 15]
target = 9

result = two_sum(nums, target)
print("Two sum result:", result)