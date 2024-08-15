from .mixins import WithWorldEntitiesMixin, WithAgentsMixin, WithPromptEnvironmentMixin


class Environment(WithWorldEntitiesMixin, WithAgentsMixin, WithPromptEnvironmentMixin):
    def __init__(self, config=None, prompts_path="prompts"):
        super(Environment, self).__init__()

        self.load_entities_from_config(config)
        self.load_agents_from_config(config)
        self.initialise_prompt_environment(prompts_path, self)
