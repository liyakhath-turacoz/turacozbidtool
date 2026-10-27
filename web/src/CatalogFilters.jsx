import React, {useState} from 'react';

export const emptyCatalogFilters = () => ({categories:[],product_types:[],canonical_types:[],brands:[],years:[],specs:{},sort:'Newest'});

function Choices({label,rows=[],selected=[],onToggle}) {
  const [search,setSearch]=useState('');
  const [expanded,setExpanded]=useState(false);
  const choices=[...rows,...selected.filter(value=>!rows.some(row=>String(row.value)===value)).map(value=>({value,count:0}))];
  const matching=choices.filter(row=>String(row.label||row.value).toLowerCase().includes(search.toLowerCase()));
  const showAll=['Categories','Product type'].includes(label);
  return <details className="catalog-facet" open={label==='Product type'}>
    <summary>{label}{selected.length?` (${selected.length})`:''}</summary>
    {rows.length>12&&<input aria-label={`Search ${label.toLowerCase()} filters`} placeholder={`Find ${label.toLowerCase()}`} value={search} onChange={event=>setSearch(event.target.value)}/>}
    <div className="catalog-facet-values">{matching.slice(0,showAll||expanded?matching.length:25).map(row=><label className="check" key={row.value}><input type="checkbox" checked={selected.includes(String(row.value))} onChange={()=>onToggle(String(row.value))}/><span>{row.value==='unknown'?'Year not supplied':row.label||row.value}</span><small>{Number(row.count).toLocaleString()}</small></label>)}</div>
    {!showAll&&matching.length>25&&<button type="button" className="link-button" onClick={()=>setExpanded(value=>!value)}>{expanded?'Show fewer':'Show all values'}</button>}
  </details>;
}

export default function CatalogFilters({facets={},filters,onChange,specsOnly=false}) {
  const scopeKey=JSON.stringify([filters.categories||[],filters.product_types||[],filters.category||'',filters.product_type||'']);
  const toggle=(key,value)=>{
    const next={...filters,[key]:(filters[key]||[]).includes(value)?filters[key].filter(item=>item!==value):[...(filters[key]||[]),value]};
    if(key==='canonical_types')Object.assign(next,{specs:{},categories:[],product_types:[]});
    onChange(next);
  };
  return <div className="catalog-facets">
    {!specsOnly&&<>
      <Choices label="Product type" rows={facets.canonical_types} selected={filters.canonical_types||[]} onToggle={value=>toggle('canonical_types',value)}/>
      <Choices key={`brand:${scopeKey}`} label="Brand / manufacturer" rows={facets.brands} selected={filters.brands} onToggle={value=>toggle('brands',value)}/>
    </>}
    <Choices label="Release year" rows={facets.years} selected={filters.years||[]} onToggle={value=>toggle('years',value)}/>
    {Object.entries(facets.specs||{}).map(([key,facet])=><Choices key={key} label={facet.label} rows={facet.values} selected={filters.specs?.[key]||[]} onToggle={value=>{
      const selected=filters.specs?.[key]||[];
      onChange({...filters,specs:{...filters.specs,[key]:selected.includes(value)?selected.filter(item=>item!==value):[...selected,value]}});
    }}/>)}
  </div>;
}

export function catalogParams(filters,extras={}) {
  const {categories=[],product_types=[],canonical_types=[],brands=[],years=[],specs={},sort='Newest'}=filters;
  return {categories,product_types,canonical_types,brands,years,specs:JSON.stringify(specs),sort,...extras};
}
