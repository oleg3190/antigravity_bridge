"""Quick SDK compatibility smoke test."""

from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig, types


def main() -> None:
    print("Agent:", Agent)
    print("LocalAgentConfig:", LocalAgentConfig)
    print("CapabilitiesConfig:", CapabilitiesConfig)
    print("Builtin tools:", [x.value for x in types.BuiltinTools])


if __name__ == "__main__":
    main()
