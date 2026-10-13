async page => {
  for (const frame of page.frames()) {
    const locator = frame.locator('input[id="form-controls-native-text"]');
    if (await locator.count() === 1) await locator.evaluate(el => el.scrollIntoView({block:'center',inline:'center',behavior:'instant'}));
  }
  return true;
}