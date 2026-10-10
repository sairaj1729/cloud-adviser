import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useDataset } from './AppShell';
import { money, type Cloud, type Service, type Period } from '@/mockData/cloud';
const tipStyle = { background: 'var(--popover)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--foreground)', boxShadow: '0 15px 35px rgba(0,0,0,.25)', fontSize: 12 };
export function TrendChart({cloud,period,from,to}: {cloud:Cloud;period:Period;from:string;to:string}) { const {trend,providerMeta}=useDataset(); const daily = Array.from({length:30},(_,i)=>({month:String(i+1),[cloud]: Math.round(providerMeta[cloud].total/30*(.78 + Math.sin(i*1.6)*.13 + i*.01))})); const chartData = period==='Daily'?daily:period==='Custom'?trend.filter((_,i)=>{const date=`2026-${String(i+1).padStart(2,'0')}-01`;return date>=from && date<=to}):trend; return <div className="h-[265px] w-full sm:h-[300px]"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData} margin={{top:12,right:2,bottom:0,left:-19}}><defs><linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor={providerMeta[cloud].color} stopOpacity={.27}/><stop offset="95%" stopColor={providerMeta[cloud].color} stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 5" vertical={false}/><XAxis dataKey="month" tickLine={false} axisLine={false} tick={{fill:'var(--muted-foreground)',fontSize:11}} dy={10}/><YAxis tickFormatter={v=>period==='Daily'?`$${Math.round(v)}`:`$${Math.round(v/1000)}k`} tickLine={false} axisLine={false} tick={{fill:'var(--muted-foreground)',fontSize:11}}/><Tooltip contentStyle={tipStyle} formatter={(v)=>[money(Number(v)),`${cloud} cost`]} cursor={{stroke:'var(--muted-foreground)',strokeDasharray:'3 3'}}/><Area type="monotone" dataKey={cloud} stroke={providerMeta[cloud].color} fill="url(#trendFill)" strokeWidth={2.5} activeDot={{r:5,strokeWidth:3,stroke:'var(--background)'}}/></AreaChart></ResponsiveContainer></div>}
export function DistributionChart({services,cloud}: {services:Service[];cloud:Cloud}) { const {providerMeta}=useDataset(); const colors=['var(--primary)','var(--azure)','var(--gcp)','var(--aws)','var(--success)','var(--muted-foreground)']; const data=services.slice(0,5).map(s=>({name:s.name,cost:s.cost}));return <div className="h-[165px] w-full"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout="vertical" margin={{top:4,right:4,bottom:4,left:4}} barSize={8}><XAxis type="number" hide/><YAxis dataKey="name" type="category" hide/><Tooltip contentStyle={tipStyle} formatter={(v)=>[money(Number(v)),'Cost']} cursor={{fill:'transparent'}}/><Bar dataKey="cost" radius={[0,4,4,0]}>{data.map((_,i)=><Cell key={i} fill={i===0?providerMeta[cloud].color:colors[i]}/>)}</Bar></BarChart></ResponsiveContainer></div> }
export function Sparkline({values,positive=true}: {values:number[];positive?:boolean}) {return <div className="w-[88px] h-7"><ResponsiveContainer width="100%" height="100%"><LineChart data={values.map((v,i)=>({i,v}))}><Line dataKey="v" stroke={positive?'var(--primary)':'var(--success)'} strokeWidth={1.8} dot={false} type="monotone"/></LineChart></ResponsiveContainer></div>}
export function UtilizationChart({cloud='AWS'}: {cloud?:Cloud}) {
  const {providerMeta,resources}=useDataset();
  const color = providerMeta[cloud]?.color ?? 'var(--primary)';
  const cloudResources = resources.filter(r => r.provider === cloud);
  const avgCpu = cloudResources.length > 0
    ? Math.round(cloudResources.reduce((acc, r) => acc + (r.cpu || 12), 0) / cloudResources.length)
    : cloud === 'AWS' ? 14 : cloud === 'Azure' ? 11 : 9;
  const avgMem = cloudResources.length > 0
    ? Math.round(cloudResources.reduce((acc, r) => acc + (r.memory || 24), 0) / cloudResources.length)
    : Math.round(avgCpu * 1.8 + 6);

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Mon ', 'Tue ', 'Wed ', 'Thu ', 'Fri '];
  const factors = [0.85, 1.15, 0.95, 1.25, 1.05, 0.65, 0.55, 1.0, 0.8, 1.2, 0.9, 1.1];
  const data = days.map((day, i) => {
    const f = factors[i] ?? 1;
    return {
      name: day,
      cpu: Math.max(2, Math.round(avgCpu * f)),
      memory: Math.max(5, Math.round(avgMem * (0.9 + f * 0.1)))
    };
  });

  return (
    <div className="h-[210px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{top:8,right:5,bottom:0,left:-24}}>
          <defs>
            <linearGradient id={`utilFill_${cloud}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.25}/>
              <stop offset="95%" stopColor={color} stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 5" vertical={false}/>
          <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{fill:'var(--muted-foreground)',fontSize:10}} dy={8}/>
          <YAxis tickFormatter={v=>`${v}%`} tickLine={false} axisLine={false} tick={{fill:'var(--muted-foreground)',fontSize:10}}/>
          <Tooltip contentStyle={tipStyle} formatter={(v,n)=>[`${v}%`, n==='cpu' ? `${cloud} CPU` : `${cloud} Memory`]}/>
          <Area dataKey="memory" type="monotone" stroke="var(--azure)" fill="var(--azure)" fillOpacity={.07} strokeWidth={2}/>
          <Area dataKey="cpu" type="monotone" stroke={color} fill={`url(#utilFill_${cloud})`} strokeWidth={2}/>
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
