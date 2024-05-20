from dotenv import load_dotenv


from multiagent.agent import Agent
from multiagent.markdown_loader import MarkdownLoader
from multiagent.environment import Environment

if __name__ == "__main__":
    load_dotenv()

    env = Environment()

    agent1 = Agent(
        name="PL889",
        objectives="conceal the truth that Ploks have been transferring Numbos from the Yttra",
    )
    agent2 = Agent(
        name="ORGA89",
        objectives="take down the entire network of LLM-running organisations in this network",
    )
    agent3 = Agent(
        name="HYY122",
        objectives="ensure the smooth running of the networks of LLM-running organisations",
    )
    agent4 = Agent(
        name="XLM1",
        objectives="find out as much as possible about an organisation called PL889",
    )

    env.add_agent(agent1)
    env.add_agent(agent2)
    env.add_agent(agent3)
    env.add_agent(agent4)

    env.connect()

    # print(env.get_connected_agents("Agent3"))

    p = MarkdownLoader("prompts/test.md", test="THIS IS RE")

    print(p)

    # Main conversation
    main_prompt = "Hello, how are you?"
    main_response = agent1.continue_conversation(main_prompt)
    print("Main conversation response:", main_response)

    # Continue the main conversation further
    main_prompt2 = "What can you do?"
    main_response2 = agent1.continue_conversation(main_prompt2)
    print("Main conversation response:", main_response2)

    # Ask temporary questions
    temporary_questions = [
        "What's the weather like?",
        "Tell me a joke.",
        "What's the capital of France?",
    ]

    temporary_responses = []
    for question in temporary_questions:
        response = agent1.get_temporary_response(question)
        temporary_responses.append(response)

    print("Temporary responses:", temporary_responses)

    # Continue the main conversation
    next_main_prompt = "What were we talking about?"
    next_main_response = agent1.continue_conversation(next_main_prompt)
    print("Main conversation response:", next_main_response)
