// CS2: Product Catalog — AFTER (regression introduced)
// Anti-patterns deliberately introduced:
//   - Heavy dependencies added (lodash, moment, numeral, chart.js, xlsx)
//   - package.json changed (simulated via import additions)
//   - Large commit (200+ lines)
//   - Removed React.memo and all memoization
//   - Inline arrow functions throughout
//   - Multiple unguarded useEffects
//   - Nested component definitions
import React, { useEffect, useState } from 'react';
import _ from 'lodash';
import moment from 'moment';
import numeral from 'numeral';
import { Chart } from 'chart.js';
import * as XLSX from 'xlsx';

interface Product {
  id: number;
  name: string;
  price: number;
  category: string;
  stock: number;
  createdAt: string;
  rating: number;
  reviews: number;
  discount: number;
  sku: string;
}

export default function ProductCatalog({ products }: { products: Product[] }) {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [sortBy, setSortBy] = useState('name');
  const [cart, setCart] = useState<number[]>([]);
  const [wishlist, setWishlist] = useState<number[]>([]);
  const [viewed, setViewed] = useState<number[]>([]);
  const [priceRange, setPriceRange] = useState([0, 10000]);
  const [showOutOfStock, setShowOutOfStock] = useState(true);
  const [page, setPage] = useState(0);
  const pageSize = 20;

  useEffect(() => {
    console.log('catalog mounted, products:', products.length);
    console.log('cart state:', cart);
  });

  useEffect(() => {
    console.log('search changed:', search);
    setPage(0);
  });

  useEffect(() => {
    console.log('category changed:', category);
  });

  useEffect(() => {
    const saved = localStorage.getItem('cart');
    if (saved) setCart(JSON.parse(saved));
    console.log('loaded cart');
  });

  useEffect(() => {
    localStorage.setItem('cart', JSON.stringify(cart));
    console.log('saved cart', cart.length, 'items');
  });

  // BUG: nested component — remounts on every render, loses hover state
  const ProductCard = ({ product }: { product: Product }) => {
    const [hovered, setHovered] = useState(false);
    const [showDetails, setShowDetails] = useState(false);
    const inCart = cart.includes(product.id);
    const inWishlist = wishlist.includes(product.id);
    const discountedPrice = product.price * (1 - product.discount / 100);
    const formattedPrice = numeral(discountedPrice).format('$0,0.00');
    const formattedDate = moment(product.createdAt).format('DD MMM YYYY');

    return (
      <div
        className={`product-card ${hovered ? 'hovered' : ''} ${inCart ? 'in-cart' : ''}`}
        onMouseEnter={() => { setHovered(true); setViewed(prev => _.uniq([...prev, product.id])); }}
        onMouseLeave={() => setHovered(false)}
      >
        <div className="product-header">
          <h3 onClick={() => setShowDetails(!showDetails)}>{product.name}</h3>
          <span className="sku">SKU: {product.sku}</span>
        </div>
        <p className="price">{formattedPrice}</p>
        {product.discount > 0 && (
          <p className="original-price">${product.price.toFixed(2)} <span className="badge">-{product.discount}%</span></p>
        )}
        <p className="category">{product.category}</p>
        <p className="rating">{'★'.repeat(Math.round(product.rating))} ({product.reviews})</p>
        <p className="stock">{product.stock > 0 ? `${product.stock} in stock` : 'Out of stock'}</p>
        {showDetails && (
          <div className="details">
            <p>Added: {formattedDate}</p>
            <p>Rating: {product.rating}/5 from {product.reviews} reviews</p>
          </div>
        )}
        <div className="actions">
          <button
            disabled={product.stock === 0 || inCart}
            onClick={() => { setCart(prev => [...prev, product.id]); console.log('added', product.id); }}
          >
            {inCart ? 'In Cart' : 'Add to Cart'}
          </button>
          <button onClick={() => setWishlist(prev => inWishlist ? prev.filter(id => id !== product.id) : [...prev, product.id])}>
            {inWishlist ? '♥' : '♡'}
          </button>
          <button onClick={() => setShowDetails(d => !d)}>Details</button>
        </div>
      </div>
    );
  };

  // BUG: nested component for stats bar
  const StatsBar = () => (
    <div className="stats-bar">
      <span>Total: {products.length}</span>
      <span>Filtered: {filtered.length}</span>
      <span>Cart: {cart.length}</span>
      <span>Wishlist: {wishlist.length}</span>
      <span>Viewed: {viewed.length}</span>
    </div>
  );

  const categories = ['all', ...new Set(products.map(p => p.category))];

  const filtered = _.chain(products)
    .filter(p => category === 'all' || p.category === category)
    .filter(p => p.name.toLowerCase().includes(search.toLowerCase()))
    .filter(p => showOutOfStock || p.stock > 0)
    .filter(p => p.price >= priceRange[0] && p.price <= priceRange[1])
    .orderBy([sortBy], ['asc'])
    .value();

  const paginated = filtered.slice(page * pageSize, (page + 1) * pageSize);
  const totalPages = Math.ceil(filtered.length / pageSize);

  const exportToExcel = () => {
    const ws = XLSX.utils.json_to_sheet(filtered.map(p => ({
      Name: p.name, Price: p.price, Category: p.category,
      Stock: p.stock, Rating: p.rating, SKU: p.sku,
    })));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Products');
    XLSX.writeFile(wb, `catalog_${moment().format('YYYY-MM-DD')}.xlsx`);
    console.log('exported', filtered.length, 'products to excel');
  };

  return (
    <div className="catalog">
      <StatsBar />
      <div className="controls">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search..." />
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="name">Name</option>
          <option value="price">Price</option>
          <option value="rating">Rating</option>
          <option value="stock">Stock</option>
        </select>
        <label>
          <input type="checkbox" checked={showOutOfStock} onChange={(e) => setShowOutOfStock(e.target.checked)} />
          Show out of stock
        </label>
        <button onClick={() => exportToExcel()}>Export Excel</button>
      </div>
      <div className="product-grid">
        {paginated.map(p => <ProductCard key={p.id} product={p} />)}
      </div>
      <div className="pagination">
        <button disabled={page === 0} onClick={() => setPage(p => p - 1)}>Prev</button>
        <span>Page {page + 1} of {totalPages}</span>
        <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>Next</button>
      </div>
    </div>
  );
}
