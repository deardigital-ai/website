---
layout: default
permalink: /
---

# {% t global.title %}

{% t global.description %}

## {% t global.latest_posts %}

<ul>
{% assign posts = site.posts | where: lang, site.lang | sort: "date" | reverse | uniq %}
{% for post in posts %}
  <li>
    <a href="{{ post.url | prepend: site.baseurl }}">{{ post.title }}</a>
    <span class="post-meta">- {{ post.date | date: "%B %-d, %Y" }}</span>
  </li>
{% endfor %}
</ul>
test