async page => {
  const viewport = await page.evaluate(() => ({width:innerWidth,height:innerHeight}));
  const matches = [], scrolls = [];
  for (const [index, frame] of page.frames().entries()) {
    scrolls.push({index,url:frame.url(),...await frame.evaluate(() => ({x:scrollX,y:scrollY}))});
    const locator = frame.locator('input[id="form-controls-native-text"]');
    for (let i = 0; i < await locator.count(); i++) {
      const box = await locator.nth(i).boundingBox();
      matches.push({box, in_viewport:!!box && box.x >= 0 && box.y >= 0 && box.x+box.width <= viewport.width && box.y+box.height <= viewport.height});
    }
  }
  return {viewport,matches,scrolls};
}