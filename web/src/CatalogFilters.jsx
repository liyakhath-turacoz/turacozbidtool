import React, {useState} from 'react';

export const emptyCatalogFilters = () => ({categories:[],product_types:[],brands:[],years:[],specs:{},minimum:'',maximum:'',sort:'Newest'});

function Choices({label,rows=[],selected=[],onToggle}) {
  const [search,setSearch]=useState('');
  const [expanded,setExpanded]=useState(false);
  const matching=rows.filter(row=>String(row.value).toLowerCase().includes(search.toLowerCase()));
  return <details className="catalog-facet" open={['Categories','Product type','Release year'].includes(label)}>
    <summary>{label}{selected.length?` (${selected.length})`:''}</summary>
    {rows.length>12&&<input aria-label={`Search ${label.toLowerCase()} filters`} placeholder={`Find ${label.toLowerCase()}`} value={search} onChange={event=>setSearch(event.target.value)}/>}
    <div className="catalog-facet-values">{matching.slice(0,expanded?matching.length:25).map(row=><label className="check" key={row.value}><input type="checkbox" checked={selected.includes(String(row.value))} onChange={()=>onToggle(String(row.value))}/><span>{row.value==='unknown'?'Year not supplied':row.value}</span><small>{Number(row.count).toLocaleString()}</small></label>)}</div>
    {matching.length>25&&<button type="button" className="link-button" onClick={()=>setExpanded(value=>!value)}>{expanded?'Show fewer':'Show all values'}</button>}
  </details>;
}

export default function CatalogFilters({facets={},filters,onChange,specsOnly=false}) {
  const toggle=(key,value)=>onChange({...filters,[key]:(filters[key]||[]).includes(value)?filters[key].filter(item=>item!==value):[...(filters[key]||[]),value]});
  const toggleSpec=(key,value)=>{
    const values=filters.specs?.[key]||[];
    const next=values.includes(value)?values.filter(item=>item!==value):[...values,value];
    const specs={...filters.specs,[key]:next};if(!next.length)delete specs[key];
    onChange({...filters,specs});
  };
  return <div className="catalog-facets">
    {!specsOnly&&<>
      <Choices label="Categories" rows={facets.categories} selected={filters.categories} onToggle={value=>toggle('categories',value)}/>
      <Choices label="Product type" rows={facets.product_types} selected={filters.product_types} onToggle={value=>toggle('product_types',value)}/>
      <Choices label="Brand / manufacturer" rows={facets.brands} selected={filters.brands} onToggle={value=>toggle('brands',value)}/>
    </>}
    <Choices label="Release year" rows={facets.years} selected={filters.years||[]} onToggle={value=>toggle('years',value)}/>
    {(facets.specifications||[]).map(facet=><Choices key={facet.key} label={facet.label} rows={facet.values} selected={filters.specs?.[facet.key]||[]} onToggle={value=>toggleSpec(facet.key,value)}/>)}
  </div>;
}

export function catalogParams(filters,extras={}) {
  return {...filters,...extras,specs:JSON.stringify(filters.specs||{})};
}
