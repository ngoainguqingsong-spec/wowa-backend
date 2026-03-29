import sys

def run(input_path: str):
    return f"REAL_PROCESS::{input_path}"

if __name__ == "__main__":
    input_path = sys.argv[1]
    result = run(input_path)
    print(result)