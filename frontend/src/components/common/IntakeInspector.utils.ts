const typeLabelMap: Record<string, string> = {
  bug: '缺陷',
  feature: '新功能',
  enhancement: '优化',
  question: '问题',
  mixed: '混合',
}

export function getTypeLabel(type: string): string {
  return typeLabelMap[type] || type
}
