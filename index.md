---
layout: default
title: Educational Blog
---

# Welcome to My Educational Blog

Here you'll find posts about education, learning, and personal development.

## Latest Posts

{% for post in site.posts %}
  * [{{ post.title }}]({{ post.url }}) - {{ post.date | date: "%B %-d, %Y" }}
{% endfor %}
