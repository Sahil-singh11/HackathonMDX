/**
 * Pillar presentation framework.  FROZEN once merged — consume, do not edit.
 *
 * Import from this barrel, never from the individual files:
 *   import { PillarPage, Answer, FigureRow, Foldable, BarComparison } from '../../components/pillar'
 *
 * The slot order (Answer -> Figures -> Visual -> Detail -> Method -> Limits) is
 * the contract: every pillar reads the same way, so nobody has to relearn where
 * the conclusion is. Need a variant? Compose it inside YOUR pillar folder and
 * pass it into a slot. Never edit this directory.
 */
export { default as PillarPage, type PillarPageProps } from './PillarPage'
export { default as Answer, type HeroNumber } from './Answer'
export { default as FigureRow, type Figure } from './FigureRow'
export { default as Foldable } from './Foldable'
export { default as BarComparison, type BarItem } from './BarComparison'
