import json
from router import QueryRouter, QueryType


def run_tests():
    router = QueryRouter()

    with open("router_test_data.json", "r", encoding="utf-8") as f:
        test_data = json.load(f)

    correct = 0

    for item in test_data:
        query = item["query"]
        expected = item["expected"]

        predicted = router.route(query).name

        is_correct = predicted == expected

        if is_correct:
            correct += 1

        print(f"Query: {query}")
        print(f"Expected: {expected}")
        print(f"Predicted: {predicted}")
        print(f"Correct: {is_correct}")
        print("-" * 50)

    accuracy = correct / len(test_data)

    print(f"\nAccuracy: {accuracy:.2f}")


if __name__ == "__main__":
    run_tests()