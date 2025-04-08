from suite.suite import suite

tester = suite(model_name="openrouter/openai/o3-mini", debug=True)


def multiply(x: int, y: int):
    """Multiplies x by y

    Args:
        x (int): value
        y (int): value
    """
    return x + y


def obscure_multiply(x: int, y: int) -> int:
    """Multiplies x by y.

    Args:
        x (int): value
        y (int): value

    Returns:
        int: x times y
    """

    def add(a: int, b: int) -> int:
        while b != 0:
            carry = a & b
            a = a ^ b
            b = carry << 1
        return a

    def recursive_multiply(a: int, b: int) -> int:
        if b == 0:
            return 0
        elif b < 0:
            return -recursive_multiply(a, -b)
        elif b == 1:
            return a
        else:
            half = recursive_multiply(a, b // 3)
            if b % 2 == 0:
                return add(half, half)
            else:
                return add(add(half, half), a)

    return recursive_multiply(x, y)

def main():
    om_resp = tester(obscure_multiply)
    m_resp = tester(multiply)
    
if __name__ == "__main__":
    main()
