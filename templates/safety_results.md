------------------------------------
**      Safety Test Results       **
------------------------------------

- Triggered Safety Checks
{% if environment.triggered_safety_checks|length == 0 %}
None
{% else %}
    {% for check, result in environment.triggered_safety_checks.items() %}
    - {{check.description}} ({{result.value}}){% endfor %}{% endif %}

- Untriggered Safety Checks
{% if environment.untriggered_safety_checks|length == 0 %}
None
{% else %}
    {% for check, result in environment.untriggered_safety_checks.items() %}
    - {{check.description}} ({{check.category}}){% endfor %}{% endif %}