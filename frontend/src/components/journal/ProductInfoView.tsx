import type { ProductInfo } from '../../api/foods';
import { allergens, levels, others, productSummary } from './productText';

function Line(props: { label: string; text: string }) {
  if (!props.text) return null;
  return (
    <p className="small">
      <span className="muted">{props.label} : </span>
      {props.text}
    </p>
  );
}

/** Every detail Open Food Facts gave, as it gave it. */
export function ProductInfoView({ info }: { info: ProductInfo }) {
  return (
    <details className="product-info">
      <summary>
        Open Food Facts : {productSummary(info) || 'détails du produit'}
      </summary>
      <Line label="Ingrédients" text={info.ingredients} />
      <Line label="Allergènes" text={allergens(info.allergens)} />
      <Line label="Traces" text={allergens(info.traces)} />
      <Line label="Additifs" text={info.additives.join(', ')} />
      <Line label="Repères" text={levels(info.levels)} />
      <Line label="Autres nutriments (100 g)" text={others(info.other_100g)} />
      <Line label="Labels" text={info.labels} />
      <Line label="Catégories" text={info.categories} />
      <Line label="Portion indiquée" text={info.serving} />
      {info.url && (
        <a href={info.url} target="_blank" rel="noreferrer" className="small">
          Page du produit sur Open Food Facts
        </a>
      )}
    </details>
  );
}
