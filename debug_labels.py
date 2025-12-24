lines = open("cockpit/app.py").readlines()
new_lines = []
for l in lines:
    if 'selected_labels = sac.tree(' in l:
        new_lines.append(f'            st.write(f"DEBUG LABELS: {{current_selection_labels}}")\n')
        new_lines.append(l)
    else:
        new_lines.append(l)

with open("cockpit/app.py", "w") as f:
    f.writelines(new_lines)
