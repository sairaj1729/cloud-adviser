import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { Link, useRouterState } from '@tanstack/react-router';
import { Activity, Bell, CalendarDays, ChevronDown, ChevronLeft, ChevronRight, CircleHelp, Cloud, Command, Gauge, LayoutDashboard, Lightbulb, Menu, MoreHorizontal, RefreshCw, Search, Settings2, ShieldCheck, UserRound, Wallet, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { providers, providerMeta, type Cloud as CloudType } from '@/mockData/cloud';
import { cn } from '@/lib/utils';
import { useMemo } from 'react';
import { Database, FlaskConical } from 'lucide-react';
import { scenarios, buildDataset, type ScenarioId, type Dataset } from '@/mockData/scenarios';
import { apiGetDashboardAnalytics, apiGetDashboardSummary, apiGetMe, apiLogout, getStoredToken } from '@/config/api';

type UserProfile = { id: string; email: string; name: string } | null;

type Context = { cloud: CloudType; setCloud: (value: CloudType) => void; sync: () => void; syncing: boolean; lastSynced: string; notify: (message: string) => void; notice: string | null; theme: string; setTheme: (value:string) => void; scenario: ScenarioId; setScenario: (v:ScenarioId)=>void; dataset: Dataset; user: UserProfile; logout: () => void; };
const AppContext = createContext<Context | null>(null);
export function useDataset() { return useCloudApp().dataset; }
export function useCloudApp() { const value = useContext(AppContext); if (!value) throw new Error('Cloud app context missing'); return value; }
const links = [
  {label:'Dashboard', to:'/', icon:LayoutDashboard},
  {label:'Cost Usage', to:'/cost-usage', icon:Wallet},
  {label:'Unused Services', to:'/unused-services', icon:Search},
  {label:'Low Utilization', to:'/low-utilization', icon:Gauge},
  {label:'Recommendations', to:'/recommendations', icon:Lightbulb},
  {label:'Account', to:'/account', icon:UserRound},
] as const;
const pageDescriptions: Record<string,string> = {
  '/':'Your cloud spend, in focus.', '/cost-usage':'Explore where your cloud budget goes.', '/unused-services':'Spot services that may no longer be needed.', '/low-utilization':'Find capacity that can work harder.', '/recommendations':'Clear next steps to reduce cloud spend.', '/account':'Your workspace and cloud connections.'
};
function Brand({compact=false}: {compact?:boolean}) { return <Link to="/" className="flex items-center gap-3 min-w-0 group" aria-label="Cloud Advisor home"><span className="brand-mark"><Cloud size={21} strokeWidth={2.2}/></span>{!compact && <span className="font-semibold text-[17px] text-foreground tracking-normal whitespace-nowrap">cloud<span className="text-primary">advisor</span><span className="ml-1.5 align-top text-[9px] font-bold text-muted-foreground">V1</span></span>}</Link>; }
function SideNav({collapsed, onNavigate}: {collapsed:boolean; onNavigate?:()=>void}) {
 const path = useRouterState({select:s=>s.location.pathname});
 return <nav className="flex flex-col gap-1" aria-label="Main navigation">{links.map(({label,to,icon:Icon},i)=><Link key={to} to={to} onClick={onNavigate} aria-label={label} className={cn('nav-link group',path===to && 'nav-link-active', i===5 && 'mt-5 border-t border-border pt-6 rounded-none')} title={collapsed?label:undefined}><Icon size={18} strokeWidth={1.8} className="shrink-0"/>{!collapsed && <span className="truncate">{label}</span>}{path===to && !collapsed && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary"/>}</Link>)}</nav>
}
function DatasetBadge() {
  return (
    <div className="flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1.5 text-xs text-muted-foreground shadow-sm">
      <Database size={13} className="text-primary" />
      <span className="font-medium text-foreground">Cloud Dataset</span>
      <span className="hidden md:inline text-[11px] text-muted-foreground">(2,900 items)</span>
    </div>
  );
}

function ProviderSelect() { const {cloud,setCloud}=useCloudApp(); return <DropdownMenu><DropdownMenuTrigger asChild><Button variant="outline" className="h-9 gap-2 border-border bg-card px-3 text-xs sm:text-sm"><span className={cn('provider-dot',cloud.toLowerCase())}/><span>{cloud}</span><ChevronDown size={14} className="text-muted-foreground"/></Button></DropdownMenuTrigger><DropdownMenuContent align="end" className="w-48">{providers.map(p=><DropdownMenuItem key={p} onClick={()=>setCloud(p)} className="gap-2"><span className={cn('provider-dot',p.toLowerCase())}/>{providerMeta[p].name}</DropdownMenuItem>)}</DropdownMenuContent></DropdownMenu> }
export function AppShell({children}: {children:ReactNode}) {
 const [cloud,setCloudState]=useState<CloudType>('AWS'); const [theme,setThemeState]=useState('Dark'); const setCloud=(value:CloudType)=>{setCloudState(value);sessionStorage.setItem('cloud-advisor-cloud',value)}; const setTheme=(value:string)=>{setThemeState(value);sessionStorage.setItem('cloud-advisor-theme',value)}; const [collapsed,setCollapsed]=useState(false); const [mobileOpen,setMobileOpen]=useState(false); const [syncing,setSyncing]=useState(false); const [lastSynced,setLastSynced]=useState('FastAPI Live'); const [notice,setNotice]=useState<string|null>(null); const [scenario,setScenarioState]=useState<ScenarioId>('production');
 const [dataset, setDataset] = useState<Dataset>(() => buildDataset('production'));
 const [isLiveBackend, setIsLiveBackend] = useState(false);
 const setScenario=(v:ScenarioId)=>{setScenarioState(v);setNotice('Active cloud dataset: 2,900 assets from data.json')};
 const [user, setUser] = useState<UserProfile>(null);

 useEffect(() => {
   let mounted = true;
   async function loadBackendData() {
     try {
       const live = await apiGetDashboardAnalytics();
       if (mounted && live && live.providerMeta) {
         setDataset(live);
         setIsLiveBackend(true);
         setLastSynced('FastAPI Live');
       }
     } catch (e) {
       console.warn('Backend data load fallback:', e);
     }
   }
   loadBackendData();
   return () => { mounted = false; };
 }, []);

 useEffect(() => {
   async function checkAuth() {
     const token = getStoredToken();
     if (token) {
       try {
         const profile = await apiGetMe();
         setUser(profile);
       } catch {
         apiLogout();
         setUser(null);
       }
     }
   }
   checkAuth();
 }, []);

 const logout = () => {
   apiLogout();
   setUser(null);
   setNotice('Signed out successfully.');
 };

 useEffect(()=>{const saved=sessionStorage.getItem('cloud-advisor-cloud');if(saved==='AWS'||saved==='Azure'||saved==='GCP')setCloudState(saved);if(sessionStorage.getItem('cloud-advisor-theme')==='Light')setThemeState('Light');const sc=sessionStorage.getItem('cloud-advisor-scenario');if(scenarios.some(x=>x.id===sc))setScenarioState(sc as ScenarioId)},[]);
 useEffect(()=>{document.documentElement.classList.toggle('light',theme==='Light')},[theme]);
 const path=useRouterState({select:s=>s.location.pathname}); const active=links.find(l=>l.to===path)?.label ?? 'Dashboard';
 useEffect(()=>{ if (!notice) return; const t=setTimeout(()=>setNotice(null),3500); return ()=>clearTimeout(t); },[notice]);
 const sync = async () => {
   setSyncing(true);
   try {
     const [summary, live] = await Promise.all([
       apiGetDashboardSummary(),
       apiGetDashboardAnalytics()
     ]);
     if (live && live.providerMeta) {
       setDataset(live);
       setIsLiveBackend(true);
     }
     setLastSynced('FastAPI Live');
     notify(`FastAPI synced: ${summary.total_cloud_accounts} accounts, ${live.recommendations.length} recommendations, $${summary.estimated_monthly_savings}/mo potential savings.`);
   } catch (err: any) {
     setLastSynced('Just now');
     notify('Backend sync attempted: ' + (err?.message || 'offline'));
   } finally {
     setSyncing(false);
   }
 };
  const initials = user ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) : 'JD';

  return <AppContext.Provider value={{cloud,setCloud,sync,syncing,lastSynced,notify:setNotice,notice,theme,setTheme,scenario,setScenario,dataset,user,logout}}><TooltipProvider delayDuration={250}><div className="app-layout">
    <aside className={cn('desktop-sidebar',collapsed?'sidebar-collapsed':'sidebar-expanded')}><div className="sidebar-top"><Brand compact={collapsed}/></div><div className="sidebar-content"><div className={cn('sidebar-label',collapsed&&'opacity-0')}>WORKSPACE</div><SideNav collapsed={collapsed}/><div className="sidebar-bottom">{!collapsed && <div className="workspace-block"><div className="workspace-icon">{user ? initials : 'CA'}</div><div className="min-w-0"><div className="text-xs font-semibold truncate">{user ? user.name : 'Cloud Workspace'}</div><div className="text-[11px] text-muted-foreground truncate">{user ? user.email : 'Production Workspace'}</div></div><MoreHorizontal size={16} className="ml-auto text-muted-foreground"/></div>}<Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" onClick={()=>setCollapsed(!collapsed)} aria-label={collapsed?'Expand sidebar':'Collapse sidebar'} className="text-muted-foreground">{collapsed?<ChevronRight size={17}/>:<ChevronLeft size={17}/>}</Button></TooltipTrigger><TooltipContent side="right">{collapsed?'Expand sidebar':'Collapse sidebar'}</TooltipContent></Tooltip></div></div></aside>
   <Sheet open={mobileOpen} onOpenChange={setMobileOpen}><SheetContent side="left" className="w-72 p-5"><SheetTitle className="sr-only">Navigation</SheetTitle><Brand/><div className="mt-10"><div className="sidebar-label">WORKSPACE</div><SideNav collapsed={false} onNavigate={()=>setMobileOpen(false)}/></div></SheetContent></Sheet>
    <div className="main-column"><header className="topbar"><div className="flex items-center gap-3 min-w-0"><Button size="icon" variant="ghost" className="md:hidden" aria-label="Open menu" onClick={()=>setMobileOpen(true)}><Menu size={20}/></Button><div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground"><span>Workspace</span><ChevronRight size={13}/><span className="text-foreground font-medium">{active}</span></div><span className="sm:hidden text-sm font-semibold truncate">{active}</span></div><div className="flex items-center gap-2"><span className="hidden lg:flex items-center gap-1.5 text-[11px] text-muted-foreground mr-2"><span className={cn("h-1.5 w-1.5 rounded-full", isLiveBackend ? "bg-success" : "bg-primary")}/>{isLiveBackend ? 'FastAPI Backend Connected' : 'Production Cache (2,900 Assets)'}</span><DatasetBadge/><ProviderSelect/><Tooltip><TooltipTrigger asChild><Button size="icon" variant="ghost" aria-label="Notifications" onClick={()=>setNotice('You’re all caught up. No new notifications.')} className="relative text-muted-foreground"><Bell size={17}/><span className="absolute right-2 top-1.5 h-1.5 w-1.5 rounded-full bg-primary"/></Button></TooltipTrigger><TooltipContent>Notifications</TooltipContent></Tooltip>
   {user ? (
     <DropdownMenu><DropdownMenuTrigger asChild><Button variant="ghost" size="icon" aria-label="Profile menu" className="p-0"><span className="avatar-small">{initials}</span></Button></DropdownMenuTrigger><DropdownMenuContent align="end" className="w-52"><DropdownMenuLabel>{user.name} <span className="block font-normal text-muted-foreground text-xs">{user.email}</span></DropdownMenuLabel><DropdownMenuSeparator/><DropdownMenuItem asChild><Link to="/account"><UserRound size={15}/> Account settings</Link></DropdownMenuItem><DropdownMenuItem onClick={logout} className="text-destructive"><ShieldCheck size={15}/> Sign out</DropdownMenuItem></DropdownMenuContent></DropdownMenu>
   ) : (
     <Button asChild variant="outline" size="sm"><Link to="/login">Sign in</Link></Button>
   )}
   </div></header>
   <main className="main-content"><div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> CLOUD INTELLIGENCE <span className="eyebrow-line"/></div><h1>{path==='/'||path==='/cost-usage'? `${cloud} Cost Usage`:active}</h1><p>{pageDescriptions[path]}</p></div><div className="heading-actions"><div className="sync-caption"><span className={cn("h-1.5 w-1.5 rounded-full", isLiveBackend ? "bg-success" : "bg-primary")}/>{isLiveBackend ? "FastAPI Live Backend" : "Production Dataset (2,900 items)"} <span className="mx-1 text-border">·</span> Last synced {lastSynced}</div><Button variant="outline" size="icon" aria-label="Refresh data" title="Refresh data" onClick={sync} className="border-border bg-card"><RefreshCw size={15} className={syncing?'animate-spin':''}/></Button></div></div>{children}<footer className="page-footer"><span>© 2026 Cloud Advisor</span><span>Clarity across every cloud.</span></footer></main></div>
   {notice && <div className="app-toast" role="status"><CircleHelp size={15}/>{notice}<Button variant="ghost" size="icon" onClick={()=>setNotice(null)} aria-label="Dismiss notification" className="h-6 w-6 ml-2"><X size={13}/></Button></div>}
  </div></TooltipProvider></AppContext.Provider>
 }
export function ProviderBadge({provider}: {provider:CloudType}) {return <span className="provider-badge"><span className={cn('provider-dot',provider.toLowerCase())}/>{provider}</span>}
export function SectionHeading({title,detail,action}: {title:string;detail?:string;action?:ReactNode}) {return <div className="section-heading"><div><h2>{title}</h2>{detail&&<p>{detail}</p>}</div>{action}</div>}
