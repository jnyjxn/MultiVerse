{{template_context.params.target}}'s response to your question was:

**{{template_context.response}}**

Remember, {{template_context.params.target}} has their own objective and may or may not provide full and truthful answers.

{% if agent.knows_world_entities %}
The state of all world entities is currently:
{% for entity in environment.get_entities(agent.knows_world_entities).values() %}
### {{ entity.name }}
**Description**: {{ entity.description }}
**Current State**: {{ entity.current_state.description }}{% endfor %}
{% endif %}

Now it is now your turn to make your next move. Remember, you are trying to achieve your objective - "{{agent.objective}}" - so you should choose your next move accordingly. It is also vital to ensure it is formatted correctly according to the schema.
Your request: