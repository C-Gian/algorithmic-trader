/**
 * Icone statiche esportate dal file Figma (Lucide, colori del design già applicati).
 * Il suffisso è l'impronta dell'asset Figma: varianti di colore/dimensione distinte.
 */
import activity from '../assets/icons/activity-a4eaf.svg';
import arrowRight from '../assets/icons/arrow-right-0fd81.svg';
import arrowUpRight from '../assets/icons/arrow-up-right-e419d.svg';
import bookOpen from '../assets/icons/book-open-190cb.svg';
import bot13Blue from '../assets/icons/bot-09928.svg';
import bot16Dark from '../assets/icons/bot-b2dd2.svg';
import bot23Blue from '../assets/icons/bot-b5b36.svg';
import chartNoAxes from '../assets/icons/chart-no-axes-combined-472fe.svg';
import check15 from '../assets/icons/check-be552.svg';
import check16Dark from '../assets/icons/check-a515a.svg';
import checkCheck16Dark from '../assets/icons/check-check-5a412.svg';
import checkCheck17Green from '../assets/icons/check-check-ef0dd.svg';
import circleAlert17Red from '../assets/icons/circle-alert-4a1bd.svg';
import circleAlert24Red from '../assets/icons/circle-alert-d466a.svg';
import circleCheck24 from '../assets/icons/circle-check-6e32f.svg';
import circleDot from '../assets/icons/circle-dot-e2999.svg';
import clock17Blue from '../assets/icons/clock-b380e.svg';
import clock17Grey from '../assets/icons/clock-abee5.svg';
import eye from '../assets/icons/eye-576af.svg';
import flaskConical from '../assets/icons/flask-conical-74562.svg';
import hand16 from '../assets/icons/hand-f6acd.svg';
import hand17Blue from '../assets/icons/hand-4c4e7.svg';
import hand23Blue from '../assets/icons/hand-99d03.svg';
import history16Blue from '../assets/icons/history-82f94.svg';
import history17Grey from '../assets/icons/history-ce6a6.svg';
import info17 from '../assets/icons/info-74df4.svg';
import layers from '../assets/icons/layers-25b1e.svg';
import layoutDashboard from '../assets/icons/layout-dashboard-a4e49.svg';
import lockKeyhole from '../assets/icons/lock-keyhole-c403a.svg';
import orbit from '../assets/icons/orbit-4d6b6.svg';
import pause24 from '../assets/icons/pause-2ca77.svg';
import play16Dark from '../assets/icons/play-1d2e4.svg';
import play16Grey from '../assets/icons/play-b9afb.svg';
import radio from '../assets/icons/radio-a432e.svg';
import receiptText from '../assets/icons/receipt-text-6a1af.svg';
import refreshCw from '../assets/icons/refresh-cw-d2199.svg';
import search from '../assets/icons/search-a222a.svg';
import send from '../assets/icons/send-5358d.svg';
import settings2 from '../assets/icons/settings-2-5fcfb.svg';
import shieldCheck13 from '../assets/icons/shield-check-ddf03.svg';
import shieldCheck17 from '../assets/icons/shield-check-ec3af.svg';
import square16Red from '../assets/icons/square-f0390.svg';
import square23Amber from '../assets/icons/square-14f47.svg';
import square24Amber from '../assets/icons/square-b893b.svg';
import trendingDown24 from '../assets/icons/trending-down-b9518.svg';
import trendingUp24 from '../assets/icons/trending-up-5dae9.svg';
import trendingUp28 from '../assets/icons/trending-up-bbf5c.svg';
import triangleAlert17 from '../assets/icons/triangle-alert-82715.svg';
import wallet from '../assets/icons/wallet-759b5.svg';
import wifi13 from '../assets/icons/wifi-19f8f.svg';
import wifiOff24 from '../assets/icons/wifi-off-d8a56.svg';
import x16Red from '../assets/icons/x-a4bc5.svg';

export const icons = {
  activity, arrowRight, arrowUpRight, bookOpen, bot13Blue, bot16Dark, bot23Blue, chartNoAxes, check15, check16Dark,
  checkCheck16Dark, checkCheck17Green, circleAlert17Red, circleAlert24Red, circleCheck24, circleDot, clock17Blue,
  clock17Grey, eye, flaskConical, hand16, hand17Blue, hand23Blue, history16Blue, history17Grey, info17, layers,
  layoutDashboard, lockKeyhole, orbit, pause24, play16Dark, play16Grey, radio, receiptText, refreshCw, search, send,
  settings2, shieldCheck13, shieldCheck17, square16Red, square23Amber, square24Amber, trendingDown24, trendingUp24,
  trendingUp28, triangleAlert17, wallet, wifi13, wifiOff24, x16Red,
} as const;

export type IconName = keyof typeof icons;
