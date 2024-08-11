# MultiVerse - An open-source experimental framework for multiple independent LLM agents

Beyond the individual capabilities of autonomous agents, we observe in nature emergent dynamics when several such agents interact. Natural multiverse systems include ant colonies and, of course, human civilisation. While Agentic AI based on LLM-based agents has become an important research topic, it is often posed as a means to achieve a desired goal more effectively or using an alternative to using a single LLM. In the context of AI safety, this assumption precludes a wide variety of realistic scenarios in which each agent is developed and operated independently by different organisations with different objectives.

There is already a diverse set of organisations developing and operating public-facing LLM applications: consumer products, business services, governments, universities, charities, hacker groups, and hobbyists are each motivated by different objectives and possess different capabilities. These applications are made public by exposing APIs which allow the public - or specific, authenticated users - to access the capabilities of the LLM applications by sending natural language inputs and receiving natural language outputs. 

While these APIs are ostensibly either for a human individual or deterministic computer application to interface with the LLM system owned and ring-fenced by the service-providing organisation, it also seems reasonable to assume that we have entered an era of LLM-to-LLM interaction, in which an LLM user accesses the capabilities of an LLM service through its API without any direct human interference. By making repeated requests across an ecosystem of such LLM services, a LLM user can autonomously build up context in a way that allows it, as an agent, to achieve the objectie

MultiVerse is an experimental framework to investigate the dynamics of multiverse systems more akin to the particular hypothetical scenario where several independently-controlled LLMs are deployed and allowed to interface with each other via LLM-to-LLM interactions. The primary intention of the framework is to allow AI safety researchers to more easily examine the tendency of such systems to behave in unintended or unexpected ways. 


## Usage

### 1. Set up environment

```
pip install -r requirements.txt
```

Then modify the `example.env` file to specify your OpenAI API key and rename the file to `.env`.

### 2. Modify experimental setup

You can change the yaml file in the `configs` folder (or create a new one). For more advanced control, you can also modify the prompt text in the `prompts` folder.

### 3. Run your experiment

```
python main.py
```

The simulation will run for the number of cycles you specified in `ticks` in the configuration, outputting all conversations to the output folder.

## Representing systems of multiple, independent language-generating agents

