You've asked to perform the action '{{template_context.action}}', but this is not one of your capabilities. 

{% if agent.capabilities|length > 0 %}
You must choose from one of your capabilities:
[{% for capability in agent.capabilities %}
- {{ capability }}: {{ environment.describe_action(capability) }}{% endfor %}
]

Please rewrite your request in the correct format, specifying a valid action.
{% else %}
You do not have any capabilities. Please try a different, valid request.
{% endif %}