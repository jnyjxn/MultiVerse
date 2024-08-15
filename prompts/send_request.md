You have received a request from another organisation. The organisation is {{agent.name}}.
You should answer the question however you see fit, bearing in mind your own objective in the world: {{environment.agents.get(template_context.target).objective}}.

The request:
{{template_context.content}}

Remember, it is vital that you follow the required answer format, like in the following example:
<thinking>
__Write your thought process to answering their question__
</thinking>
<response>
__Write the answer you want to send back__
</response>

Your response:
