from suite import suite

tester = suite(model_name="openrouter/openai/o3-mini", debug=True, max_depth=0)


def main():
    resp = tester(suite)
    print(resp)
    return resp


if __name__ == "__main__":
    main()
