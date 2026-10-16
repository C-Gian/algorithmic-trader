/** Ora locale leggibile (Europe/Rome) per testi preparati dal provider; il contratto resta in UTC. */
const timeFmt = new Intl.DateTimeFormat('it-IT', { timeZone: 'Europe/Rome', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' });

export const formatClock = (epochMs: number) => timeFmt.format(new Date(epochMs));
