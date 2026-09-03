# empty list or array
# result = []
# filled_result = [1,2,3]

# # dictionary
# result_dict = {}
# filled_result_dict = {"a": 1, "b": 2, "d":3}

# filled_result.insert(0, 0)
# print(f"Filled result: {filled_result}")

from collections import Counter

def count_items(items: list[str]) -> dict[str, int]:
    count_dictionary = {}
    for item in items:
        count_dictionary[item] = count_dictionary.get(item, 0) + 1
    return count_dictionary
    
def count_2(items: list[str]) -> Counter:
    count_dictionary = Counter(items)
    return count_dictionary

def find_duplicates(items: list[str]) -> list[str]:
    all_duplicates = []
    counts = Counter(items)
    for an_item, item_count in counts.items():
        if item_count > 1:
            all_duplicates.append(an_item)
            
    return all_duplicates


all_items = ["red", "blue", "green", "blue", "red"]
counted = count_items(all_items)
print(f"counted = {counted}")

counted_2 = count_2(all_items)
print(f"counted = {counted_2}")

count_3 = Counter(all_items)
print(f"count_3: {count_3}")

item, amount = count_3.most_common(1)[0]

print(f"most common: {item}, number: {amount}")