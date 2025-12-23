{% if CONTEXT %}
<previous_context>
Here are some recent analyses for this repository to provide context on ongoing work or style:

{% for item in CONTEXT %}
---
**Date**: {{ item.timestamp }}
**Model**: {{ item.model }}
**Previous Analysis**:
{{ item.response }}
{% endfor %}
</previous_context>
{% endif %}
