import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { Link, useRouterState } from '@tanstack/react-router';
import { Activity, Bell, Building2, Check, ChevronDown, ChevronLeft, ChevronRight, CircleHelp, Cloud, Database, Gauge, LayoutDashboard, Lightbulb, Menu, MoreHorizontal, RefreshCw, Search, ShieldCheck, ShoppingBag, Sparkles, Store, UserRound, Wallet, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { providers, providerMeta, type Cloud as CloudType } from '@/mockData/cloud';
import { cn } from '@/lib/utils';
import { scenarios, buildDataset, type ScenarioId, type Dataset } from '@/mockData/scenarios';
import { apiGetDashboardAnalytics, apiGetDashboardSummary, apiGetMe, apiLogout, apiListDatasets, apiSwitchDataset, type DatasetMeta, getStoredToken } from '@/config/api';

type UserProfile = { id: string; email: string; name: string } | null;

type Context = {
  cloud: CloudType;
  setCloud: (value: CloudType) => void;
  sync: () => void;
  syncing: boolean;
  isLoading: boolean;
  isFetching: boolean;
  lastSynced: string;
  notify: (message: string) => void;
  notice: string | null;
  theme: string;
  setTheme: (value:string) => void;
  scenario: ScenarioId;
  setScenario: (v:ScenarioId)=>void;
  dataset: Dataset;
  hasLoadedBackend: boolean;
  user: UserProfile;
  logout: () => void;
  activeDatasetId: string;
  datasetsList: DatasetMeta[];
  switchDataset: (id: string) => Promise<void>;
};

const AppContext = createContext<Context | null>(null);
export function useDataset() { return useCloudApp().dataset; }
export function useCloudApp() { const value = useContext(AppContext); if (!value) throw new Error('Cloud app context missing'); return value; }

const links = [
  {label:'Dashboard', to:'/', icon:LayoutDashboard},
  {label:'Cost Usage', to:'/cost-usage', icon:Wallet},
  {label:'Unused Services', to:'/unused-services', icon:Search},
  {label:'Low Utilization', to:'/low-utilization', icon:Gauge},
  {label:'Recommendations', to:'/recommendations', icon:Lightbulb},
  {label:'AI Recommendations', to:'/ai-recommendations', icon:Sparkles},
  {label:'Account', to:'/account', icon:UserRound},
] as const;

const pageDescriptions: Record<string,string> = {
  '/':'Your cloud spend, in focus.',
  '/cost-usage':'Explore where your cloud budget goes.',
  '/unused-services':'Spot services that may no longer be needed.',
  '/low-utilization':'Find capacity that can work harder.',
  '/recommendations':'Clear next steps to reduce cloud spend.',
  '/ai-recommendations':'LLM-driven fleet rightsizing, SKU transitions, and automated CLI runbooks.',
  '/account':'Your workspace and cloud connections.'
};

function Brand({compact=false}: {compact?:boolean}) {
  return (
    <Link to="/" className="flex items-center gap-3 min-w-0 group" aria-label="Cloud Advisor home">
      <span className="brand-mark"><Cloud size={21} strokeWidth={2.2}/></span>
      {!compact && (
        <span className="font-semibold text-[17px] text-foreground tracking-normal whitespace-nowrap">
          cloud<span className="text-primary">advisor</span>
          <span className="ml-1.5 align-top text-[9px] font-bold text-muted-foreground">V1</span>
        </span>
      )}
    </Link>
  );
}

function SideNav({collapsed, onNavigate}: {collapsed:boolean; onNavigate?:()=>void}) {
  const path = useRouterState({select:s=>s.location.pathname});
  return (
    <nav className="flex flex-col gap-1" aria-label="Main navigation">
      {links.map(({label,to,icon:Icon},i)=>(
        <Link
          key={to}
          to={to}
          onClick={onNavigate}
          aria-label={label}
          className={cn('nav-link group',path===to && 'nav-link-active', i===6 && 'mt-5 border-t border-border pt-6 rounded-none')}
          title={collapsed?label:undefined}
        >
          <Icon size={18} strokeWidth={1.8} className="shrink-0"/>
          {!collapsed && <span className="truncate">{label}</span>}
          {path===to && !collapsed && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary"/>}
        </Link>
      ))}
    </nav>
  );
}

function DatasetSelector({
  datasets,
  activeDatasetId,
  isSwitching,
  onSelectDataset,
}: {
  datasets: DatasetMeta[];
  activeDatasetId: string;
  isSwitching: boolean;
  onSelectDataset: (id: string) => void;
}) {
  const activeDataset = datasets.find(d => d.id === activeDatasetId) || datasets[0] || {
    id: 'bank_balanced',
    name: 'Global Bank Multi-Cloud',
    domain: 'Banking & FinTech',
    item_count: 10000,
    icon: 'Building2'
  };

  const renderIcon = (iconName: string) => {
    switch (iconName) {
      case 'Building2': return <Building2 size={14} className="text-primary shrink-0" />;
      case 'ShoppingBag': return <ShoppingBag size={14} className="text-primary shrink-0" />;
      case 'Store': return <Store size={14} className="text-primary shrink-0" />;
      default: return <Database size={14} className="text-primary shrink-0" />;
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="h-9 gap-2 border-border bg-card px-2.5 sm:px-3 text-xs sm:text-sm font-medium hover:bg-accent/40"
          title="Switch dataset: Evaluates Rule Engine across AWS, Azure & GCP and stores findings in MongoDB"
        >
          {isSwitching ? (
            <RefreshCw size={14} className="animate-spin text-primary shrink-0" />
          ) : (
            renderIcon(activeDataset.icon)
          )}
          <span className="truncate max-w-[110px] sm:max-w-[170px] text-foreground font-semibold">
            {isSwitching ? 'Evaluating Fleet...' : activeDataset.name}
          </span>
          <span className="hidden lg:inline text-[11px] text-muted-foreground font-normal bg-secondary px-1.5 py-0.5 rounded border border-border">
            {activeDataset.item_count ? `${activeDataset.item_count.toLocaleString()} assets` : '10,000 assets'}
          </span>
          <ChevronDown size={14} className="text-muted-foreground shrink-0" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 p-2">
        <DropdownMenuLabel className="px-2 py-1.5">
          <div className="font-semibold text-xs text-foreground flex items-center justify-between">
            <span>Multi-Cloud Synthetic Datasets</span>
            <span className="text-[10px] font-normal text-muted-foreground uppercase tracking-wider bg-secondary px-1.5 py-0.5 rounded">Live MongoDB</span>
          </div>
          <p className="text-[11px] font-normal text-muted-foreground mt-1">
            Switch between datasets. The Rule Engine evaluates every asset into findings stored in MongoDB.
          </p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {datasets.map((d) => {
          const isSelected = d.id === activeDatasetId;
          return (
            <DropdownMenuItem
              key={d.id}
              onClick={() => onSelectDataset(d.id)}
              className={cn(
                "flex items-start gap-2.5 p-2 rounded-md cursor-pointer transition-colors",
                isSelected && "bg-primary/10 text-primary focus:bg-primary/15"
              )}
            >
              <div className="mt-0.5 p-1.5 rounded-md bg-secondary/80 border border-border shrink-0">
                {renderIcon(d.icon)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-foreground truncate">{d.name}</span>
                  {isSelected && <Check size={14} className="text-primary shrink-0 ml-1" />}
                </div>
                <div className="text-[11px] text-muted-foreground truncate mt-0.5">
                  {d.domain} · {d.item_count?.toLocaleString()} items
                </div>
                {d.description && (
                  <div className="text-[10px] text-muted-foreground/80 line-clamp-1 mt-0.5">
                    {d.description}
                  </div>
                )}
              </div>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function ProviderSelect() {
  const {cloud,setCloud}=useCloudApp();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="h-9 gap-2 border-border bg-card px-3 text-xs sm:text-sm">
          <span className={cn('provider-dot',cloud.toLowerCase())}/>
          <span>{cloud}</span>
          <ChevronDown size={14} className="text-muted-foreground"/>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {providers.map(p=>(
          <DropdownMenuItem key={p} onClick={()=>setCloud(p)} className="gap-2">
            <span className={cn('provider-dot',p.toLowerCase())}/>
            {providerMeta[p].name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function AppShell({children}: {children:ReactNode}) {
  const [cloud,setCloudState]=useState<CloudType>('AWS');
  const [theme,setThemeState]=useState('Dark');
  const setCloud=(value:CloudType)=>{setCloudState(value);sessionStorage.setItem('cloud-advisor-cloud',value)};
  const setTheme=(value:string)=>{setThemeState(value);sessionStorage.setItem('cloud-advisor-theme',value)};
  const [collapsed,setCollapsed]=useState(false);
  const [mobileOpen,setMobileOpen]=useState(false);
  const [isLoading, setIsLoading]=useState<boolean>(true);
  const [syncing,setSyncing]=useState<boolean>(false);
  const [lastSynced,setLastSynced]=useState<string>('Connecting...');
  const [notice,setNotice]=useState<string|null>(null);
  const [scenario,setScenarioState]=useState<ScenarioId>('bank_balanced');
  const [dataset, setDataset] = useState<Dataset>(() => buildDataset('bank_balanced'));
  const [hasLoadedBackend, setHasLoadedBackend] = useState<boolean>(false);
  const [isLiveBackend, setIsLiveBackend] = useState<boolean>(false);

  const [datasetsList, setDatasetsList] = useState<DatasetMeta[]>([
    {
      id: "bank_balanced",
      name: "Global Bank Multi-Cloud",
      domain: "Banking & FinTech",
      description: "Tier-1 Global Bank (10,000 balanced assets across AWS, Azure, GCP)",
      file: "bank_resources_aws_azure_gcp_balanced.json",
      item_count: 10000,
      icon: "Building2",
      is_active: true,
      loaded_resources: 10000,
      generated_findings: 2820
    },
    {
      id: "retail_balanced",
      name: "Enterprise Retail Fleet",
      domain: "Retail & E-Commerce",
      description: "Enterprise Retail & Supply Chain (10,000 balanced assets across AWS, Azure, GCP)",
      file: "retail_resources_aws_azure_gcp_balanced.json",
      item_count: 10000,
      icon: "ShoppingBag",
      is_active: false,
      loaded_resources: 10000,
      generated_findings: 2377
    },
    {
      id: "retail_2900",
      name: "Mid-Market Retail Fleet",
      domain: "Retail Operations",
      description: "Mid-Market Omnichannel Retail (2,900 assets from data.json)",
      file: "data.json",
      item_count: 2900,
      icon: "Store",
      is_active: false,
      loaded_resources: 2900,
      generated_findings: 105
    }
  ]);
  const [activeDatasetId, setActiveDatasetId] = useState<string>("bank_balanced");

  const isFetching = isLoading || syncing || !hasLoadedBackend;
  const setScenario=(v:ScenarioId)=>{
    setScenarioState(v);
    switchDataset(v);
  };
  const [user, setUser] = useState<UserProfile>(null);

  useEffect(() => {
    let mounted = true;
    async function loadBackendData() {
      setIsLoading(true);
      try {
        const [liveList, live] = await Promise.all([
          apiListDatasets().catch(() => null),
          apiGetDashboardAnalytics(false).catch(() => null)
        ]);

        if (liveList && liveList.length > 0) {
          setDatasetsList(liveList);
          const active = liveList.find(d => d.is_active);
          if (active) setActiveDatasetId(active.id);
        }

        if (mounted && live && live.providerMeta) {
          setDataset(live);
          if (live.scenario?.id) {
            setActiveDatasetId(live.scenario.id);
          }
          setIsLiveBackend(true);
          setHasLoadedBackend(true);
          setLastSynced('FastAPI Live');
        }
      } catch (e) {
        console.warn('Backend data load fallback:', e);
        if (mounted) {
          setDataset(buildDataset('bank_balanced'));
          setIsLiveBackend(false);
          setHasLoadedBackend(true);
          setLastSynced('Preview Cache');
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }
    loadBackendData();
    return () => { mounted = false; };
  }, []);

  const switchDataset = async (datasetId: string) => {
    if (datasetId === activeDatasetId && isLiveBackend) return;
    setIsLoading(true);
    try {
      const live = await apiSwitchDataset(datasetId);
      if (live && live.providerMeta) {
        setDataset(live);
        setActiveDatasetId(datasetId);
        setIsLiveBackend(true);
        setHasLoadedBackend(true);
        setLastSynced('FastAPI Live');
        const targetMeta = datasetsList.find(d => d.id === datasetId);
        const name = targetMeta?.name || datasetId;
        const count = targetMeta?.item_count ? `${targetMeta.item_count.toLocaleString()} assets` : '';
        setNotice(`Switched dataset to ${name} (${count}) · Rule Engine evaluated and findings stored in MongoDB.`);
      }
      const refreshedList = await apiListDatasets().catch(() => null);
      if (refreshedList?.length) {
        setDatasetsList(refreshedList);
      }
    } catch (err: any) {
      console.error('Failed to switch dataset:', err);
      setNotice(`Failed to switch dataset: ${err.message || 'Error'}`);
    } finally {
      setIsLoading(false);
    }
  };

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

  useEffect(()=>{
    const saved=sessionStorage.getItem('cloud-advisor-cloud');
    if(saved==='AWS'||saved==='Azure'||saved==='GCP')setCloudState(saved);
    if(sessionStorage.getItem('cloud-advisor-theme')==='Light')setThemeState('Light');
  },[]);

  useEffect(()=>{document.documentElement.classList.toggle('light',theme==='Light')},[theme]);
  const path=useRouterState({select:s=>s.location.pathname});
  const active=links.find(l=>l.to===path)?.label ?? 'Dashboard';

  useEffect(()=>{
    if (!notice) return;
    const t=setTimeout(()=>setNotice(null),4000);
    return ()=>clearTimeout(t);
  },[notice]);

  const sync = async () => {
    setSyncing(true);
    try {
      const [summary, live, refreshedList] = await Promise.all([
        apiGetDashboardSummary(activeDatasetId),
        apiGetDashboardAnalytics(true, activeDatasetId),
        apiListDatasets().catch(() => null)
      ]);
      if (live && live.providerMeta) {
        setDataset(live);
        setIsLiveBackend(true);
        setHasLoadedBackend(true);
      }
      if (refreshedList && refreshedList.length > 0) {
        setDatasetsList(refreshedList);
      }
      setLastSynced('FastAPI Live');
      setNotice(`FastAPI synced: ${summary.total_resources?.toLocaleString() || '10,000'} resources, ${live.recommendations.length} recommendations, $${summary.estimated_monthly_savings?.toLocaleString()}/mo potential savings.`);
    } catch (err: any) {
      setLastSynced('Just now');
      setNotice('Backend sync attempted: ' + (err?.message || 'offline'));
    } finally {
      setSyncing(false);
    }
  };

  const initials = user ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) : 'JD';

  const pageTitles: Record<string, string> = {
    '/': `${cloud} Cost Usage`,
    '/cost-usage': `${cloud} Cost Usage`,
    '/unused-services': `${cloud} Unused Services`,
    '/low-utilization': `${cloud} Low Utilization`,
    '/recommendations': `${cloud} Recommendations`,
    '/ai-recommendations': `${cloud} AI Recommendations`,
    '/account': 'Account Settings',
  };
  const activeDescriptions: Record<string, string> = {
    '/': `Your ${cloud} cloud spend and optimization opportunities, in focus.`,
    '/cost-usage': `Explore where your ${cloud} budget goes.`,
    '/unused-services': `Spot ${cloud} services that may no longer be needed.`,
    '/low-utilization': `Find ${cloud} capacity that can work harder.`,
    '/recommendations': `Clear next steps to reduce ${cloud} spend.`,
    '/ai-recommendations': `Deep LLM-driven fleet rightsizing, hardware transitions, and automated CLI runbooks.`,
    '/account': 'Your workspace and cloud connections.'
  };

  return (
    <AppContext.Provider value={{
      cloud, setCloud, sync, syncing, isLoading, isFetching,
      lastSynced, notify:setNotice, notice, theme, setTheme,
      scenario, setScenario, dataset, hasLoadedBackend, user, logout,
      activeDatasetId, datasetsList, switchDataset
    }}>
      <TooltipProvider delayDuration={250}>
        <div className="app-layout">
          <aside className={cn('desktop-sidebar',collapsed?'sidebar-collapsed':'sidebar-expanded')}>
            <div className="sidebar-top"><Brand compact={collapsed}/></div>
            <div className="sidebar-content">
              <div className={cn('sidebar-label',collapsed&&'opacity-0')}>WORKSPACE</div>
              <SideNav collapsed={collapsed}/>
              <div className="sidebar-bottom">
                {!collapsed && (
                  <div className="workspace-block">
                    <div className="workspace-icon">{user ? initials : 'CA'}</div>
                    <div className="min-w-0">
                      <div className="text-xs font-semibold truncate">{user ? user.name : 'Cloud Workspace'}</div>
                      <div className="text-[11px] text-muted-foreground truncate">{user ? user.email : 'Multi-Cloud Fleet'}</div>
                    </div>
                    <MoreHorizontal size={16} className="ml-auto text-muted-foreground"/>
                  </div>
                )}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" onClick={()=>setCollapsed(!collapsed)} aria-label={collapsed?'Expand sidebar':'Collapse sidebar'} className="text-muted-foreground">
                      {collapsed?<ChevronRight size={17}/>:<ChevronLeft size={17}/>}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">{collapsed?'Expand sidebar':'Collapse sidebar'}</TooltipContent>
                </Tooltip>
              </div>
            </div>
          </aside>

          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetContent side="left" className="w-72 p-5">
              <SheetTitle className="sr-only">Navigation</SheetTitle>
              <Brand/>
              <div className="mt-10">
                <div className="sidebar-label">WORKSPACE</div>
                <SideNav collapsed={false} onNavigate={()=>setMobileOpen(false)}/>
              </div>
            </SheetContent>
          </Sheet>

          <div className="main-column">
            <header className="topbar">
              <div className="flex items-center gap-3 min-w-0">
                <Button size="icon" variant="ghost" className="md:hidden" aria-label="Open menu" onClick={()=>setMobileOpen(true)}>
                  <Menu size={20}/>
                </Button>
                <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
                  <span>Workspace</span>
                  <ChevronRight size={13}/>
                  <span className="text-foreground font-medium">{active}</span>
                </div>
                <span className="sm:hidden text-sm font-semibold truncate">{active}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="hidden lg:flex items-center gap-1.5 text-[11px] text-muted-foreground mr-1">
                  <span className={cn("h-1.5 w-1.5 rounded-full", isFetching ? "bg-primary animate-ping" : isLiveBackend ? "bg-success" : "bg-primary")}/>
                  {isFetching ? 'Syncing Fleet & Evaluating Rules...' : isLiveBackend ? 'FastAPI & MongoDB Connected' : 'Production Cache'}
                </span>
                <DatasetSelector
                  datasets={datasetsList}
                  activeDatasetId={activeDatasetId}
                  isSwitching={isLoading}
                  onSelectDataset={switchDataset}
                />
                <ProviderSelect/>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button size="icon" variant="ghost" aria-label="Notifications" onClick={()=>setNotice('You’re all caught up. No new notifications.')} className="relative text-muted-foreground">
                      <Bell size={17}/>
                      <span className="absolute right-2 top-1.5 h-1.5 w-1.5 rounded-full bg-primary"/>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Notifications</TooltipContent>
                </Tooltip>

                {user ? (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" aria-label="Profile menu" className="p-0">
                        <span className="avatar-small">{initials}</span>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-52">
                      <DropdownMenuLabel>
                        {user.name}
                        <span className="block font-normal text-muted-foreground text-xs">{user.email}</span>
                      </DropdownMenuLabel>
                      <DropdownMenuSeparator/>
                      <DropdownMenuItem asChild>
                        <Link to="/account"><UserRound size={15}/> Account settings</Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={logout} className="text-destructive">
                        <ShieldCheck size={15}/> Sign out
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                ) : (
                  <Button asChild variant="outline" size="sm">
                    <Link to="/login">Sign in</Link>
                  </Button>
                )}
              </div>
            </header>

            <main className="main-content">
              <div className="page-heading">
                <div>
                  <div className="eyebrow">
                    <span className="eyebrow-line"/> CLOUD INTELLIGENCE <span className="eyebrow-line"/>
                  </div>
                  <h1>{pageTitles[path] ?? active}</h1>
                  <p>{activeDescriptions[path] ?? pageDescriptions[path]}</p>
                </div>
                <div className="heading-actions">
                  <div className="sync-caption">
                    <span className={cn("h-1.5 w-1.5 rounded-full", isFetching ? "bg-primary animate-ping" : isLiveBackend ? "bg-success" : "bg-primary")}/>
                    {isFetching ? "Evaluating Multi-Cloud Fleet..." : isLiveBackend ? `${dataset.scenario?.name || 'Multi-Cloud'} (FastAPI Live)` : "Production Dataset"}
                    <span className="mx-1 text-border">·</span>
                    {isFetching ? "Syncing..." : `Last synced ${lastSynced}`}
                  </div>
                  <Button variant="outline" size="icon" aria-label="Refresh data" title="Refresh data" onClick={sync} disabled={isFetching} className="border-border bg-card">
                    <RefreshCw size={15} className={isFetching?'animate-spin text-primary':''}/>
                  </Button>
                </div>
              </div>
              {children}
              <footer className="page-footer">
                <span>© 2026 Cloud Advisor</span>
                <span>Clarity across every cloud.</span>
              </footer>
            </main>
          </div>

          {notice && (
            <div className="app-toast" role="status">
              <CircleHelp size={15}/>
              {notice}
              <Button variant="ghost" size="icon" onClick={()=>setNotice(null)} aria-label="Dismiss notification" className="h-6 w-6 ml-2">
                <X size={13}/>
              </Button>
            </div>
          )}
        </div>
      </TooltipProvider>
    </AppContext.Provider>
  );
}

export function ProviderBadge({provider}: {provider:CloudType}) {
  return (
    <span className="provider-badge">
      <span className={cn('provider-dot',provider.toLowerCase())}/>
      {provider}
    </span>
  );
}

export function SectionHeading({title,detail,action}: {title:string;detail?:string;action?:ReactNode}) {
  return (
    <div className="section-heading">
      <div>
        <h2>{title}</h2>
        {detail&&<p>{detail}</p>}
      </div>
      {action}
    </div>
  );
}

