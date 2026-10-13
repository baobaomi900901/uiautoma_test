async page => {
  for (const frame of page.frames()) await frame.evaluate(() => window.scrollTo({top:document.documentElement.scrollHeight,behavior:'instant'}));
  return true;
}