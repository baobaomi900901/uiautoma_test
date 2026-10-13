async page => {
  const results = [];
  for (const frame of page.frames()) {
    for (const id of ["form-controls-ant-text", "form-controls-native-text"]) {
      const locator = frame.locator('input[id="' + id + '"]');
      const count = await locator.count();
      for (let index = 0; index < count; index++) {
        results.push(await locator.nth(index).evaluate(el => {
          const ancestors = [];
          for (let node = el.parentElement; node && ancestors.length < 4; node = node.parentElement) {
            ancestors.push({tag: node.tagName.toLowerCase(), labels: Array.from(node.querySelectorAll('label')).map(label => ({text: label.textContent.trim(), for: label.getAttribute('for')})), text: node.textContent.trim().slice(0, 200)});
          }
          return {id: el.id, tag: el.tagName.toLowerCase(), type: el.type, placeholder: el.getAttribute('placeholder'), visible: el.getClientRects().length > 0, enabled: !el.disabled, shadowHost: el.getRootNode().host?.tagName.toLowerCase() ?? null, ancestors};
        }));
      }
    }
  }
  return {url: page.url(), count: results.length, inputs: results};
}