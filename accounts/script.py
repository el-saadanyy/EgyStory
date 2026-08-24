import re
with open('../templates/home.html', 'r', encoding='utf-8') as f:
    content = f.read()

how_idx = content.find('How EgyStory Works')
how_sec_start = content.rfind('<section', 0, how_idx)

trust_idx = content.find('Transparency You Can Trust')
trust_sec_start = content.rfind('<section', 0, trust_idx)

cta_idx = content.find('Ready to make a difference?')
cta_sec_start = content.rfind('<section', 0, cta_idx)

end_cta_sec = content.find('</section>', cta_idx) + 10
end_trust_sec = content.find('</section>', trust_idx) + 10
end_how_sec = content.find('</section>', how_idx) + 10

how_sec = content[how_sec_start:end_how_sec]
trust_sec = content[trust_sec_start:end_trust_sec]
cta_sec = content[cta_sec_start:end_cta_sec]

how_sec = re.sub(r'<section[^>]*>', '<section id=\"how-it-works\" style=\"padding: 80px 0; background-color: var(--color-bg);\">', how_sec, count=1)
trust_sec = re.sub(r'<section[^>]*>', '<section id=\"about\" style=\"padding: 80px 0; background-color: var(--color-bg);\">', trust_sec, count=1)

new_bottom = how_sec + '\n\n' + cta_sec + '\n\n' + trust_sec

min_start = min(how_sec_start, trust_sec_start, cta_sec_start)
max_end = max(end_how_sec, end_trust_sec, end_cta_sec)

new_content = content[:min_start] + new_bottom + content[max_end:]

new_content = new_content.replace('href=\"{% url \'home\' %}#about\" class=\"btn btn-outline btn-lg\" style=\"border-color: rgba(255,255,255,0.2); color: white;\">How It Works</a>', 'href=\"#how-it-works\" class=\"btn btn-outline btn-lg\" style=\"border-color: rgba(255,255,255,0.2); color: white;\">How It Works</a>')

with open('../templates/home.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
