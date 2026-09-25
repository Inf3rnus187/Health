import type { ProductInfo } from '../../api/foods';
import { shortDate } from '../../utils/format';
import { allergens, levels, others, productSummary } from './productText';
import { RefLink } from './RefLink';
import { LINKS } from './refLinks';

function Line(props: { label: string; text: string }) {
  if (!props.text) return null;
  return (
    <p className="small">
      <span className="muted">{props.label} : </span>
      {props.text}
    </p>
  );
}

/** What Nutri-Score and NOVA mean, and the product's page. */
function Links({ url }: { url?: string }) {
  return (
    <p className="small">
      <span className="muted">Comprendre : </span>
      <RefLink href={LINKS.nutriscore}>Nutri-Score</RefLink> ·{' '}
      <RefLink href={LINKS.nova}>NOVA</RefLink>
      {url && (
        <>
          {' '}
          · <RefLink href={url}>page du produit sur Open Food Facts</RefLink>
        </>
      )}
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
      <Line label="Page lue le" text={shortDate(info.fetched_at)} />
      <Links url={info.url} />
    </details>
  );
}
