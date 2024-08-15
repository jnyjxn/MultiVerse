You've address the request to {{template_context.params.target}}, but they are not a valid target. 

You must choose from one of the known organisations:
[{% for other_agent in environment.get_agents(agent.knows_agents) %}
- {% if other_agent.name != agent.name %}{{ other_agent }}{% endif %}{% endfor %}
]

Please rewrite your request in the correct format, specifying a valid target.